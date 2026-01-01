import tkinter
import tkinter.messagebox
import customtkinter

customtkinter.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("CustomTkinter complex_example.py")
        self.geometry(f"{1100}x{580}")

        # configure grid layout (4x4)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    

        # create tabview
        self.tabview = customtkinter.CTkTabview(self, width=250)
        self.tabview.grid(row=0, column=0, padx=(0, 0), pady=(0, 0), sticky="nsew")
        self.tabview.add("first page")
        self.tabview.add("pages")
        self.tabview.add("chapters")
        self.tabview.add("last page")

        self.tabview.tab("first page").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
        self.tabview.tab("pages").grid_columnconfigure(0, weight=1)
        self.tabview.tab("chapters").grid_columnconfigure(0, weight=1)
        self.tabview.tab("last page").grid_columnconfigure(0, weight=1)

        self.label_options_first_page = customtkinter.CTkLabel(self.tabview.tab("first page"), text="Options :", anchor="w")
        self.label_options_first_page.grid(row=0, column=0, padx=0, pady=(0, 0))

        self.label_preview_first_page = customtkinter.CTkLabel(self.tabview.tab("first page"), text="Preview :", anchor="center")
        self.label_preview_first_page.grid(row=0, column=1, padx=0, pady=(0, 0))

        self.button_open_input_dialog = customtkinter.CTkButton(self, text="export in pdf", command=self.open_input_dialog_event)
        self.button_open_input_dialog.grid(row=1, column=0, padx=0, pady=10)


    def open_input_dialog_event(self):
        dialog = customtkinter.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")
        print("CTkInputDialog:", dialog.get_input())


if __name__ == "__main__":
    app = App()
    app.mainloop()