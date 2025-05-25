import copy
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window, VSplit, ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import FormattedText, HTML
from prompt_toolkit.filters import Condition

class LuaStateEditor:
    def __init__(self, lua_state_dict_original):
        self.original_data = lua_state_dict_original
        self.working_data = copy.deepcopy(lua_state_dict_original) # Edit a copy
        
        self.current_path = [] # List of keys/indices representing path from root
        self.current_view_data = self.working_data # Data currently being displayed/navigated
        self.selected_index = 0 # Index in current list or dict view
        self.view_items = [] # List of (key_or_index, value) for current view

        self.user_saved = False
        
        # Edit Mode State
        self.editing_mode = False
        self.editing_path_to_parent = [] 
        self.editing_key_or_idx = None   
        self.original_value_for_edit = None
        self.error_message = "" 
        self.edit_input_area = TextArea(multiline=False, height=1, prompt="Edit: ")


        self._update_view_items()

        # --- Key Bindings ---
        self.kb = KeyBindings()
        self._setup_key_bindings()

        # --- Layout ---
        self.header_text = FormattedTextControl(text=self._get_header_text, focusable=False)
        self.path_text = FormattedTextControl(text=self._get_path_text, focusable=False)
        self.main_content_text = FormattedTextControl(text=self._get_main_content_formatted_text, focusable=True)
        self.error_line = FormattedTextControl(text=self._get_error_text, focusable=False)

        root_container = HSplit([
            Window(height=1, content=self.header_text),
            Window(height=1, content=self.path_text),
            Window(content=self.main_content_text),
            ConditionalContainer(
                content=self.edit_input_area,
                filter=Condition(lambda: self.editing_mode)
            ),
            ConditionalContainer(
                Window(height=1, content=self.error_line), 
                filter=Condition(lambda: bool(self.error_message)) 
            )
        ])

        
        self.layout = Layout(container=root_container)
        self.app = Application(layout=self.layout, key_bindings=self.kb, full_screen=True, mouse_support=False)

    def _get_header_text(self):
        edit_mode_hint = " | (Editing Mode - Enter: Submit, Esc: Cancel)" if self.editing_mode else ""
        return HTML(f"<style bg='blue' fg='white'>Lua State Editor | Up/Down: Navigate | Enter: Dive/Edit | Esc: Back | Ctrl-S: Save & Exit | Ctrl-Q: Quit{edit_mode_hint}</style>")

    def _get_path_text(self):
        return HTML(f"<style fg='cyan'>Path: {'/'.join(map(str, self.current_path))}</style>")

    def _update_view_items(self):
        self.view_items = []
        if isinstance(self.current_view_data, dict):
            self.view_items = list(self.current_view_data.items())
        elif isinstance(self.current_view_data, list):
            self.view_items = list(enumerate(self.current_view_data))
        
        # Ensure selected_index is valid
        if not self.view_items:
            self.selected_index = 0
        else:
            self.selected_index = max(0, min(self.selected_index, len(self.view_items) - 1))


    def _get_main_content_formatted_text(self):
        lines = []
        if not self.view_items:
            lines.append(HTML("<em>&lt;Empty&gt;</em>"))
        
        for i, (key_or_idx, value) in enumerate(self.view_items):
            prefix = "> " if i == self.selected_index else "  "
            
            # Display key/index
            if isinstance(self.current_view_data, dict):
                display_key = f"{key_or_idx}: "
            else: # list
                display_key = f"[{key_or_idx}] "

            # Display value (simplified for now)
            if isinstance(value, (dict, list)):
                display_value = f"&lt;{type(value).__name__} of {len(value)} items&gt;"
            else:
                display_value = repr(value) # Show strings with quotes, etc.
            
            line_html = f"{prefix}{HTML(display_key)}{HTML(display_value)}"
            if i == self.selected_index:
                line_html = f"<style bg='#444444'>{line_html}</style>" # Highlight selected line
            lines.append(HTML(line_html))
        return FormattedText(lines)


    def _get_error_text(self):
        return HTML(f"<style fg='red'>{self.error_message}</style>")

    def _start_editing_value(self):
        if not self.view_items:
            return
        
        self.editing_mode = True
        # Make a copy of current_path for the parent, as current_path itself might change
        # if we were to allow deeper navigation while editing (not current design).
        self.editing_path_to_parent = list(self.current_path) 
        
        key_or_idx, value = self.view_items[self.selected_index]
        self.editing_key_or_idx = key_or_idx
        self.original_value_for_edit = value
        
        self.edit_input_area.text = str(self.original_value_for_edit)
        self.error_message = ""
        self.app.layout.focus(self.edit_input_area)

    def _submit_edited_value(self):
        new_value_str = self.edit_input_area.text
        original_type = type(self.original_value_for_edit)
        new_value = None
        coercion_success = False

        try:
            if original_type is bool:
                if new_value_str.lower() in ['true', '1', 'yes', 't']:
                    new_value = True
                    coercion_success = True
                elif new_value_str.lower() in ['false', '0', 'no', 'f']:
                    new_value = False
                    coercion_success = True
                else:
                    self.error_message = "Invalid boolean: Use true/false, 1/0, yes/no"
            elif original_type is int:
                new_value = int(new_value_str)
                coercion_success = True
            elif original_type is float:
                new_value = float(new_value_str)
                coercion_success = True
            elif original_type is str:
                new_value = new_value_str # No coercion needed, already a string
                coercion_success = True
            else: # Should not happen if only primitives are editable
                self.error_message = f"Unsupported type for editing: {original_type.__name__}"

        except ValueError:
            self.error_message = f"Invalid value: Expected {original_type.__name__}"

        if coercion_success:
            parent_data = self.working_data
            for path_segment in self.editing_path_to_parent:
                parent_data = parent_data[path_segment]
            
            parent_data[self.editing_key_or_idx] = new_value
            
            # Update current_view_data if we edited an item in it directly
            if self.editing_path_to_parent == self.current_path:
                 self.current_view_data[self.editing_key_or_idx] = new_value

            self.editing_mode = False
            self.error_message = ""
            self._update_view_items() # Refresh main display
            self.app.layout.focus(self.main_content_text)
        else:
            # Keep editing_mode = True and focus on input area
            self.app.layout.focus(self.edit_input_area)


    def _cancel_editing_value(self):
        self.editing_mode = False
        self.error_message = ""
        self.app.layout.focus(self.main_content_text)


    def _setup_key_bindings(self):
        # Condition to disable when in editing mode
        not_editing = ~Condition(lambda: self.editing_mode)

        @self.kb.add('up', filter=not_editing)
        def _(event):
            if self.selected_index > 0:
                self.selected_index -= 1
        
        @self.kb.add('down', filter=not_editing)
        def _(event):
            if self.view_items and self.selected_index < len(self.view_items) - 1:
                self.selected_index += 1
        
        @self.kb.add('escape', filter=not_editing)
        def _(event):
            if self.current_path:
                self.current_path.pop()
                self._rebuild_current_view_from_path()
                self._update_view_items()
                self.selected_index = 0 
        
        @self.kb.add('enter', filter=not_editing)
        def _(event):
            if not self.view_items:
                return

            key_or_idx, value = self.view_items[self.selected_index]
            
            if isinstance(value, (dict, list)):
                self.current_path.append(key_or_idx)
                self.current_view_data = value
                self._update_view_items()
                self.selected_index = 0
            else: # Primitive value
                self._start_editing_value()

        # Keybindings for editing mode
        editing = Condition(lambda: self.editing_mode)

        @self.kb.add('enter', filter=editing)
        def _(event):
            self._submit_edited_value()

        @self.kb.add('escape', filter=editing)
        def _(event):
            self._cancel_editing_value()


        # Global keybindings (always active)
        @self.kb.add('c-s') 
        def _(event):
            # If in editing mode, try to submit first? Or just save as is?
            # For now, save and exit immediately. Consider behavior if editing.
            if self.editing_mode:
                self._submit_edited_value() # Attempt to submit, then exit
                if self.editing_mode: # If submit failed (e.g. validation error)
                    return # Don't exit yet
            
            self.user_saved = True
            self.app.exit(result=self.working_data)

        @self.kb.add('c-q') 
        def _(event):
            # If in editing mode, perhaps ask for confirmation or cancel edit first.
            # For now, quit immediately.
            if self.editing_mode:
                self._cancel_editing_value() # Cancel current edit before quitting
            
            self.user_saved = False
            self.app.exit(result=None)
            
    def _rebuild_current_view_from_path(self): # This is the correct, single definition
        # Navigate from self.working_data using self.current_path
        target_data = self.working_data
        for path_segment in self.current_path:
            target_data = target_data[path_segment]
        self.current_view_data = target_data


    def run(self):
        # This will block until Application.exit() is called.
        # The result passed to exit() will be returned by app.run().
        return self.app.run()

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    sample_lua_data = {
        "GameState": {
            "Resources": {"Gems": 100, "Darkness": 2000, "Keys": [1,2,3]},
            "Hero": "Zagreus",
            "RunCount": 10
        },
        "UnlockedFeatures": ["Sword", "Bow"],
        "Settings": {"Volume": 0.8, "GodMode": False},
        "EmptyList": [],
        "EmptyDict": {}
    }
    editor = LuaStateEditor(sample_lua_data)
    final_data = editor.run()

    if editor.user_saved: # Check the flag set by Ctrl-S
        print("Data saved:")
        # Basic diff or print (replace with better diff if complex)
        # For now, just print if it's different or what was returned
        if final_data != sample_lua_data: # This will be true due to deepcopy if no changes made
             print(final_data) # In real use, this would be processed further
        else: # if final_data is None (Ctrl-Q) or same as original
             print("Data was not changed or quit without saving.")
    else:
        print("Exited without saving.")
