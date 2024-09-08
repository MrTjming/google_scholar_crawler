from colorama import Fore, Style,init

# 初始化 colorama
init(autoreset=True)

def print_header(text):
    print(Fore.MAGENTA + text)

def print_blue(text):
    print(Fore.BLUE + text)

def print_cyan(text):
    print(Fore.CYAN + text)

def print_green(text):
    print(Fore.GREEN + text)

def print_yellow(text):
    print(Fore.YELLOW + text)

def print_red(text):
    print(Fore.RED + text)

def print_bold(text):
    print(Style.BRIGHT + text)
