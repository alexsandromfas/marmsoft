# import customtkinter as ctk
# from tkinter import Tk, Menu
# from tkinter import ttk

# # Inicialização do customtkinter
# ctk.set_appearance_mode("dark")  # Modo inicial: dark
# ctk.set_default_color_theme("blue")

# class ToolTip(object):
#     """
#     Classe para criar tooltips em widgets.
#     """
#     def __init__(self, widget, text='widget info'):
#         self.waittime = 500     # Tempo de espera em milissegundos
#         self.wraplength = 180   # Comprimento da quebra de linha em pixels
#         self.widget = widget
#         self.text = text
#         self.widget.bind("<Enter>", self.enter)
#         self.widget.bind("<Leave>", self.leave)
#         self.id = None
#         self.tw = None

#     def enter(self, event=None):
#         self.schedule()

#     def leave(self, event=None):
#         self.unschedule()
#         self.hidetip()

#     def schedule(self):
#         self.unschedule()
#         self.id = self.widget.after(self.waittime, self.showtip)

#     def unschedule(self):
#         id_ = self.id
#         self.id = None
#         if id_:
#             self.widget.after_cancel(id_)

#     def showtip(self, event=None):
#         x, y, cx, cy = self.widget.bbox("insert")
#         x += self.widget.winfo_rootx() + 25
#         y += self.widget.winfo_rooty() + 20
#         # Criação da janela tooltip
#         self.tw = ctk.CTkToplevel(self.widget)
#         self.tw.wm_overrideredirect(True)  # Remover bordas da janela
#         self.tw.wm_geometry("+%d+%d" % (x, y))
#         label = ctk.CTkLabel(self.tw, text=self.text, justify='left')
#         label.pack(ipadx=10, ipady=5)

#     def hidetip(self):
#         tw = self.tw
#         self.tw= None
#         if tw:
#             tw.destroy()

# class App(ctk.CTk):

#     def __init__(self):
#         super().__init__()

#         self.title("Interface CustomTkinter")
#         self.geometry("800x600")
#         self.grid_columnconfigure(1, weight=1)
#         self.grid_rowconfigure(0, weight=1)

#         # Menu superior
#         menubar = Menu(self)
#         menu_principal = Menu(menubar, tearoff=0)
#         menu_principal.add_command(label="Opção 1")
#         menu_principal.add_command(label="Opção 2")
#         menubar.add_cascade(label="Menu", menu=menu_principal)
#         menubar.add_command(label="Configurações")
#         menubar.add_command(label="Ajuda")
#         self.config(menu=menubar)

#         # Frame esquerdo com botões
#         left_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
#         left_frame.grid(row=0, column=0, sticky="nswe")
#         left_frame.grid_rowconfigure(5, weight=1)

#         button1 = ctk.CTkButton(left_frame, text="CTkButton")
#         button1.grid(row=1, column=0, padx=20, pady=10, sticky="we")
#         ToolTip(button1, text="Este é um botão CTkButton.")

#         button2 = ctk.CTkButton(left_frame, text="Disabled CTkButton", state="disabled")
#         button2.grid(row=2, column=0, padx=20, pady=10, sticky="we")
#         ToolTip(button2, text="Este botão está desativado.")

#         # Componentes de entrada e controle
#         entry = ctk.CTkEntry(self, placeholder_text="Digite algo...")
#         entry.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="we")
#         ToolTip(entry, text="Insira seu texto aqui.")

#         combobox = ctk.CTkComboBox(self, values=["Opção 1", "Opção 2", "Opção 3"])
#         combobox.grid(row=1, column=1, padx=20, pady=10, sticky="we")
#         ToolTip(combobox, text="Selecione uma opção.")

#         slider = ctk.CTkSlider(self, from_=0, to=100)
#         slider.grid(row=2, column=1, padx=20, pady=10, sticky="we")
#         ToolTip(slider, text="Ajuste o valor do slider.")

#         switch = ctk.CTkSwitch(self, text="CTkSwitch")
#         switch.grid(row=3, column=1, padx=20, pady=10)
#         ToolTip(switch, text="Ative ou desative a opção.")

#         # Rótulos e seleção
#         label = ctk.CTkLabel(self, text="CTkLabel - Exemplo de texto")
#         label.grid(row=4, column=1, padx=20, pady=10)
#         ToolTip(label, text="Este é um rótulo CTkLabel.")

#         radiobutton_var = ctk.StringVar(value="Opção 1")

#         radiobutton1 = ctk.CTkRadioButton(self, text="Opção 1", variable=radiobutton_var, value="Opção 1")
#         radiobutton1.grid(row=5, column=1, padx=20, pady=5, sticky="w")
#         ToolTip(radiobutton1, text="Selecione a opção 1.")

#         radiobutton2 = ctk.CTkRadioButton(self, text="Opção 2", variable=radiobutton_var, value="Opção 2")
#         radiobutton2.grid(row=6, column=1, padx=20, pady=5, sticky="w")
#         ToolTip(radiobutton2, text="Selecione a opção 2.")

#         checkbox = ctk.CTkCheckBox(self, text="CTkCheckBox")
#         checkbox.grid(row=7, column=1, padx=20, pady=5, sticky="w")
#         ToolTip(checkbox, text="Marque para selecionar.")

#         checkbox_disabled = ctk.CTkCheckBox(self, text="Disabled CTkCheckBox", state="disabled")
#         checkbox_disabled.grid(row=8, column=1, padx=20, pady=5, sticky="w")
#         ToolTip(checkbox_disabled, text="Este checkbox está desativado.")

#         # Seletor de modo de aparência
#         appearance_mode_label = ctk.CTkLabel(self, text="Modo de Aparência:")
#         appearance_mode_label.grid(row=9, column=1, padx=20, pady=(20, 5), sticky="w")

#         appearance_mode_optionmenu = ctk.CTkOptionMenu(self, values=["Dark", "Light"], command=self.change_appearance_mode)
#         appearance_mode_optionmenu.grid(row=10, column=1, padx=20, pady=(5, 20), sticky="we")
#         appearance_mode_optionmenu.set("Dark")
#         ToolTip(appearance_mode_optionmenu, text="Altere o modo de aparência.")

#         # Tornar a janela responsiva
#         self.columnconfigure(1, weight=1)
#         self.rowconfigure(0, weight=1)

#     def change_appearance_mode(self, new_mode):
#         ctk.set_appearance_mode(new_mode)

# if __name__ == "__main__":
#     app = App()
#     app.mainloop()


# import customtkinter as ctk
# from tkinter import Menu

# class App(ctk.CTk):
#     def __init__(self):
#         super().__init__()
#         self.title("Menu com Cascatas")
#         self.geometry("400x300")
        
#         # Menu superior
#         menubar = Menu(self)
        
#         # Menu principal
#         menu_principal = Menu(menubar, tearoff=0)
#         menu_principal.add_command(label="Opção 1", command=lambda: print("Opção 1 Selecionada"))
#         menu_principal.add_command(label="Opção 2", command=lambda: print("Opção 2 Selecionada"))
        
#         # Submenu 1
#         submenu_1 = Menu(menu_principal, tearoff=0)
#         submenu_1.add_command(label="SubOpção 1.1", command=lambda: print("SubOpção 1.1 Selecionada"))
#         submenu_1.add_command(label="SubOpção 1.2", command=lambda: print("SubOpção 1.2 Selecionada"))
#         menu_principal.add_cascade(label="Submenu 1", menu=submenu_1)
        
#         # Submenu 2 dentro do Submenu 1
#         submenu_2 = Menu(submenu_1, tearoff=0)
#         submenu_2.add_command(label="SubOpção 2.1", command=lambda: print("SubOpção 2.1 Selecionada"))
#         submenu_2.add_command(label="SubOpção 2.2", command=lambda: print("SubOpção 2.2 Selecionada"))
#         submenu_1.add_cascade(label="Submenu 2", menu=submenu_2)
        
#         # Adicionar o menu principal à barra de menu
#         menubar.add_cascade(label="Menu", menu=menu_principal)
        
#         # Outros menus
#         menubar.add_command(label="Configurações", command=lambda: print("Configurações Selecionadas"))
#         menubar.add_command(label="Ajuda", command=lambda: print("Ajuda Selecionada"))
        
#         # Configurar o menu na janela
#         self.config(menu=menubar)

# if __name__ == "__main__":
#     app = App()
#     app.mainloop()





a = 961.16
b = -323.15

# Geração de 500 pontos
num_points = 500
voltages = [0.5 + i*(1.0/(num_points-1)) for i in range(num_points)]  # 500 valores de 0.5 a 1.5

with open("dados.csv", "w", newline="", encoding="utf-8") as f:
    f.write("Voltage,Angle\n")
    for v in voltages:
        angle = a*v + b
        f.write(f"{v},{angle}\n")

print("Arquivo 'dados.csv' gerado com sucesso.")
