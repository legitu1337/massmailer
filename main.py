#github.com/legitu1337
#meow meow meow

import smtplib
import json
import logging
import os
import re
import socket
import time
import random
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style
import pyfiglet
import dns.resolver

# colorama :3
init(autoreset=True)

# Files
USAGE_FILE = "smtp_usage.json"
CONFIG_FILE = "configs.json"

# ------------------ LOCKTOBER ------------------
usage_lock = threading.RLock() 
print_lock = threading.Lock()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def safe_print(message):
    """dw bout it"""
    with print_lock:
        print(message, flush=True)

# ------------------ Logging ------------------

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        reset = Style.RESET_ALL
        message = super().format(record)
        return f"{color}{message}{reset}"

def setup_logging():
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.FileHandler('email_log.txt', mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColorFormatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_info(message): logging.info(message)
def log_warning(message): logging.warning(message)
def log_error(message): logging.error(message)

# ------------------ Banner ------------------
# pls dont remove

def show_banner():
    try:
        banner_text = pyfiglet.figlet_format("Mass-Mailer")
        safe_print(Fore.CYAN + banner_text + Style.RESET_ALL)
    except Exception:
        safe_print(Fore.CYAN + "Mass-Mailer" + Style.RESET_ALL)
        
    safe_print(Fore.YELLOW + "-" * 60 + Style.RESET_ALL)
    safe_print(Fore.RED + "Created by: legitu1337".center(60) + Style.RESET_ALL)
    safe_print(Fore.YELLOW + "-" * 60 + Style.RESET_ALL)

# ------------------ Utility Functions ------------------

def load_usage():
    with usage_lock:
        if not os.path.exists(USAGE_FILE): return {}
        try:
            with open(USAGE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_usage(usage_data):
    with usage_lock:
        try:
            with open(USAGE_FILE, "w") as f:
                json.dump(usage_data, f, indent=4)
        except Exception as e:
            log_error(f"Failed to save usage data: {e}")

def is_valid_email(email):
    regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(regex, email) is not None

def get_ip_from_hostname(hostname):
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except Exception:
        return None

def check_blacklists(ip):
    blacklist_hosts = [
        "zen.spamhaus.org",
        "bl.spamcop.net",
        "dnsbl.sorbs.net"
    ] #^^^^^^ holy OP

    reversed_ip = ".".join(reversed(ip.split(".")))
    blacklisted_on = []

    resolver = dns.resolver.Resolver()
    # fallback dns
    try:
        resolver.nameservers = ["8.8.8.8", "1.1.1.1"] 
    except Exception:
        pass
        
    # trust
    resolver.timeout = 2
    resolver.lifetime = 2

    for blacklist in blacklist_hosts:
        query = f"{reversed_ip}.{blacklist}"
        try:
            answers = resolver.resolve(query, "A")
            if answers:
                blacklisted_on.append(blacklist)
        except (dns.resolver.NXDOMAIN, dns.resolver.Timeout, dns.resolver.NoNameservers):
            continue
        except Exception:
            continue

    return blacklisted_on

def validate_config(config):
    required_fields = ["smtp_server", "port", "user", "password"]
    for field in required_fields:
        if field not in config:
            log_error(f"Missing required field in config: {field}")
            return False
    return True

# ------------------ SMTP stuff ------------------

class SMTPServer:
    def __init__(self, config, usage_data, today_str):
        self.config = config
        self.user = config["user"]
        self.daily_limit = config.get("daily_limit", 500)
        self.timeout = config.get("timeout", 10)
        self.usage_data = usage_data
        self.today_str = today_str

        with usage_lock:
            if today_str not in self.usage_data:
                self.usage_data[today_str] = {}
            self.usage_count = self.usage_data[self.today_str].get(self.user, 0)

        self.active = self.usage_count < self.daily_limit

        smtp_host = self.config["smtp_server"]
        self.smtp_ip = get_ip_from_hostname(smtp_host)

        if self.smtp_ip:
            safe_print(f"{Fore.MAGENTA}[Startup] Checking Blacklists for {self.user}...{Style.RESET_ALL}")
            
            blacklisted_on = check_blacklists(self.smtp_ip)
            if blacklisted_on:
                log_warning(f"[!]  SMTP {smtp_host} is BLACKLISTED on: {', '.join(blacklisted_on)}")
            else:
                log_info(f"[OK] SMTP {smtp_host} is Clean.")
        else:
            log_warning(f"Unable to resolve IP for SMTP host: {smtp_host}") #ur issue 100%

        if not self.active:
            safe_print(f"{Fore.YELLOW}[Limit] {self.user} reached daily limit ({self.daily_limit}).{Style.RESET_ALL}")

    def increment_usage(self):
        with usage_lock:
            if self.today_str not in self.usage_data:
                self.usage_data[self.today_str] = {}
            
            current_val = self.usage_data[self.today_str].get(self.user, 0)
            self.usage_count = current_val + 1
            self.usage_data[self.today_str][self.user] = self.usage_count
            
            save_usage(self.usage_data)

            if self.usage_count >= self.daily_limit:
                self.active = False
                safe_print(f"{Fore.YELLOW}{self.user} limit reached. Disabling.{Style.RESET_ALL}")

# ------------------ Config and Email ------------------

def load_config(config_file, usage_data, today_str):
    try:
        with open(config_file, "r") as file:
            configs = json.load(file)
            smtp_servers = []
            for config in configs:
                if validate_config(config):
                    smtp_servers.append(SMTPServer(config, usage_data, today_str))
            return smtp_servers
    except Exception as e:
        log_error(f"Error loading config file: {e}")
        return None

def load_emails(emails_file): #this only loads valid emails so u dont mess up
    valid_emails = []
    try:
        with open(emails_file, "r") as file:
            emails = file.read().splitlines()

        for email in emails:
            if is_valid_email(email):
                valid_emails.append(email)

        if not valid_emails:
            log_error("No valid emails found!")
            return None

        log_info(f"Loaded {len(valid_emails)} valid emails.")
        return valid_emails

    except Exception as e:
        log_error(f"Error loading emails file: {e}")
        return None

# ------------------ SMTP Logic ------------------

def get_next_available_smtp(smtp_servers):
    active_servers = [server for server in smtp_servers if server.active]
    return random.choice(active_servers) if active_servers else None

def send_email(smtp_server, sender_email, receiver_email, subject, html_content, max_retries, min_delay, max_delay):
    attempts = 0
    success = False
    smtp_config = smtp_server.config
    
    # prepare message content
    message = MIMEMultipart("related")
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(html_content, "html"))
    msg_str = message.as_string()

    while attempts < max_retries and not success:
        server = None
        try:
            safe_print(f"{Fore.CYAN}[Attempt {attempts+1}] Sending to {receiver_email}...{Style.RESET_ALL}")

            socket.setdefaulttimeout(15)

            # might work might not work
            port = int(smtp_config["port"])
            if port == 465:
                server = smtplib.SMTP_SSL(smtp_config["smtp_server"], port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_config["smtp_server"], port, timeout=15)
                server.starttls() 
            
            server.login(smtp_config["user"], smtp_config["password"])
            server.sendmail(sender_email, receiver_email, msg_str)
            
            smtp_server.increment_usage()
            safe_print(f"{Fore.GREEN}SUCCESS: Sent to {receiver_email}{Style.RESET_ALL}")
            log_info(f"SUCCESS: Sent to {receiver_email} via {smtp_config['user']}")
            success = True
            return (receiver_email, "Success")

        except smtplib.SMTPAuthenticationError:
            safe_print(f"{Fore.RED}AUTH FAIL: {smtp_config['user']}{Style.RESET_ALL}")
            return (receiver_email, "Auth Failed")
            
        except socket.timeout:
            safe_print(f"{Fore.YELLOW}TIMEOUT: {receiver_email} timed out.{Style.RESET_ALL}")
            
        except Exception as e:
            safe_print(f"{Fore.YELLOW}RETRYING: {receiver_email} error: {e}{Style.RESET_ALL}")
            
        finally:
            if server:
                try:
                    server.quit()
                except (smtplib.SMTPServerDisconnected, Exception):
                    try:
                        server.close()
                    except:
                        pass
        
        attempts += 1
        if attempts < max_retries:
            time.sleep(random.uniform(min_delay, max_delay))

    safe_print(f"{Fore.RED}FAILED: {receiver_email} after {max_retries} attempts.{Style.RESET_ALL}")
    return (receiver_email, f"Failed after {max_retries} attempts")

def task(receiver_email, smtp_servers, sender_email, subject, html_content, max_retries, min_delay, max_delay):
    smtp_server = get_next_available_smtp(smtp_servers)
    if not smtp_server:
        log_error(f"No available SMTP servers for {receiver_email}.")
        return (receiver_email, "No SMTP Available")

    return send_email(smtp_server, sender_email, receiver_email, subject, html_content, max_retries, min_delay, max_delay)

# ------------------ Main Function ------------------

def main():
    clear_screen()
    show_banner()
    setup_logging()

    if not os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, 'w') as f: json.dump({}, f)
    
    usage_data = load_usage()
    today_str = datetime.now().strftime("%Y-%m-%d")

    log_info("Loading configuration...")
    
    if not os.path.exists(CONFIG_FILE):
        log_error(f"Error: '{CONFIG_FILE}' not found.")
        return

    smtp_servers = load_config(CONFIG_FILE, usage_data, today_str)
    if not smtp_servers:
        log_error("No SMTP servers loaded.")
        return
    
    log_info(f"Loaded {len(smtp_servers)} SMTP servers.")

    emails_file = input(Fore.GREEN + "Enter emails file: " + Style.RESET_ALL)
    if not os.path.exists(emails_file):
        log_error("File not found.")
        return
    emails = load_emails(emails_file)
    if not emails: return

    sender_email = input(Fore.GREEN + "Enter sender email: " + Style.RESET_ALL)
    subject = input(Fore.GREEN + "Enter subject: " + Style.RESET_ALL)
    html_file = input(Fore.GREEN + "Enter HTML file: " + Style.RESET_ALL)
    
    if not os.path.exists(html_file):
        log_error("HTML file not found.")
        return

    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    try:
        print(Fore.YELLOW + "\n--- Settings ---" + Style.RESET_ALL)
        num_threads = int(input("Threads: "))
        max_retries = int(input("Max Retries: "))
        min_delay = float(input("Min Delay sec: "))
        max_delay = float(input("Max Delay sec: "))
    except ValueError:
        log_error("Invalid numbers entered.")
        return

    clear_screen()
    show_banner()
    log_info(f"Starting with {num_threads} threads...")

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(task, email, smtp_servers, sender_email, subject, html_content, max_retries, min_delay, max_delay): email
            for email in emails
        }

        for future in as_completed(futures):
            pass

    print("\n" + Fore.GREEN + "Process complete. Check 'email_log.txt' for details." + Style.RESET_ALL)

if __name__ == "__main__":
    main()
