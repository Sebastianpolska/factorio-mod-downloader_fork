"""
Main downloader module for Factorio mods with dependency resolution.
"""

import os
import time
from threading import Thread
from typing import Final
from typing import List
from typing import Set
from typing import Tuple

import chromedriver_autoinstaller
import requests
from bs4 import BeautifulSoup
from CTkMessagebox import CTkMessagebox
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from factorio_mod_downloader.downloader.helpers import find_free_port
from factorio_mod_downloader.downloader.helpers import generate_anticache
from factorio_mod_downloader.downloader.helpers import is_port_free
from factorio_mod_downloader.downloader.helpers import is_website_up


# API Constants
BASE_FACTORIO_MOD_URL: Final = "https://mods.factorio.com/mod"
BASE_MOD_URL: Final = "https://re146.dev/factorio/mods/en#"
BASE_DOWNLOAD_URL: Final = "https://mods-storage.re146.dev"


class ModDownloader(Thread):
    """Thread-based mod downloader with dependency resolution."""

    def __init__(self, mod_url: str, output_path: str, app):
        super().__init__()
        self.daemon = True
        self.output_path = output_path
        self.mod = mod_url.split("/")[-1]
        self.mod_url = BASE_MOD_URL + mod_url
        self.app = app
        self.downloaded_mods: Set[str] = set()
        self.analyzed_mods: Set[str] = set()
        self.chrome_options: Options = None
        self.download_threads = []
        self.include_optional = self.app.optional_deps.get()
        # Pobieramy wybraną wersję Factorio z GUI (np. "2.0")
        self.target_factorio_version = self.app.factorio_version.get()

    def run(self):
        """Execute the download process."""
        try:
            self.log_info(f"Targeting Factorio version: {self.target_factorio_version}\n")
            self.log_info(f"Loading mod {self.mod}.\n")

            if not is_website_up(BASE_MOD_URL):
                raise Exception("Website down. Please check your connection.")

            self.chrome_options = self._init_selenium()
            self.download_mod_with_dependencies(self.mod_url, self.output_path)

            active_threads = [t for t in self.download_threads if t.is_alive()]
            if active_threads:
                self.log_info("Waiting for all downloads to finish...\n")
                self.app.progress_file.after(
                    0, lambda: self.app.progress_file.configure(text="Finalizing downloads...")
                )

                for t in active_threads:
                    t.join()

            self.log_info("All mods downloaded successfully.\n")
            self.app.progress_file.after(
                0,
                lambda: self.app.progress_file.configure(text="All mods downloaded successfully."),
            )

            CTkMessagebox(
                title="Download Completed",
                width=500,
                wraplength=500,
                message="Mods successfully downloaded.",
                icon="check",
                option_1="Ok",
            )

        except Exception as e:
            error_msg = str(e).split("\n")[0]
            self.log_info(f"Error: {error_msg}\n")

            CTkMessagebox(
                title="Error",
                width=500,
                wraplength=500,
                message=f"Download failed.\n{error_msg}",
                icon="cancel",
            )

            self.app.progress_file.after(
                0,
                lambda: self.app.progress_file.configure(text="Start download to see progress."),
            )

        finally:
            self.app.download_button.configure(state="normal", text="Start Download")
            self.app.path_button.configure(state="normal")

    def _init_selenium(self) -> Options:
        """Initialize Selenium WebDriver options."""
        try:
            self.app.progress_file.after(
                0,
                lambda: self.app.progress_file.configure(
                    text="Downloading and loading dependencies."
                ),
            )

            self.log_info("Downloading application dependencies.\n")
            chromedriver_autoinstaller.install()
            self.log_info("Finished downloading application dependencies.\n")

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-position=-2400,-2400")
            chrome_options.add_argument("--disable-gpu")

            port = find_free_port()
            chrome_options.add_argument(f"--remote-debugging-port={port}")

            self.log_info("Configured application dependencies.\n")
            return chrome_options

        except Exception as e:
            self.log_info(f"Error initializing Selenium: {str(e).split('\n')[0]}\n")
            raise

    def init_driver(self) -> webdriver.Chrome:
        return webdriver.Chrome(options=self.chrome_options)

    def close_driver(self, driver: webdriver.Chrome):
        try:
            driver.stop_client()
            driver.close()
            driver.quit()
        except Exception as e:
            print(f"Error closing driver: {str(e).split('\n')[0]}")

    def get_page_source(self, url: str, is_dependency_check: bool = False) -> BeautifulSoup:
        driver = self.init_driver()
        try:
            driver.get(url)
            if is_dependency_check:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.panel-hole"))
                )
            else:
                time.sleep(2)
            html = driver.page_source
            return BeautifulSoup(html, "html.parser")
        except Exception as e:
            self.log_info(f"Error loading {url}: {str(e).split('\n')[0]}\n")
            return None
        finally:
            self.close_driver(driver)

    def get_mod_name(self, soup: BeautifulSoup) -> str:
        dd_element = soup.find("dd", id="mod-info-name")
        if not dd_element:
            raise ValueError("Could not find mod name in page")
        return dd_element.get_text(strip=True).strip()

    def get_latest_version(self, soup: BeautifulSoup) -> str:
        """Extract the mod version suitable for selected Factorio version."""
        select = soup.find("select", {"id": "mod-version"})
        if not select:
            raise ValueError("No version select element found")

        options = select.find_all("option")
        
        # Przeszukujemy listę wersji w poszukiwaniu dopasowania do wybranej wersji gry (np. "2.0")
        # Mirror re146.dev zazwyczaj ma opisy typu "0.1.0 (2.0)" lub podaje wersję gry w tekście.
        for option in options:
            if self.target_factorio_version in option.text:
                return option["value"]

        # Jeśli nie znaleziono idealnego dopasowania, bierzemy domyślny mechanizm (last)
        for option in options:
            if "(last)" in option.text:
                return option["value"]

        # Ostateczny fallback
        first_option = options[0] if options else None
        if not first_option:
            raise ValueError("No version options found")

        return first_option["value"]

    def get_required_dependencies(self, mod_name: str) -> List[Tuple[str, str]]:
        dependency_url = (
            f"{BASE_FACTORIO_MOD_URL}/{mod_name}/dependencies?direction=out&sort=idx&filter=all"
        )
        try:
            soup = self.get_page_source(dependency_url, is_dependency_check=True)
            if not soup:
                self.log_info(f"Could not fetch dependencies for {mod_name}\n")
                return []

            required_mods = []
            links = soup.find_all("a", class_="mod-dependencies-required")
            for link in links:
                dep_name = link.get_text(strip=True)
                mod_url = f"{BASE_MOD_URL}{BASE_FACTORIO_MOD_URL}/{dep_name}"
                required_mods.append((dep_name, mod_url))

            if self.include_optional:
                for link in soup.find_all("a", class_="mod-dependencies-optional"):
                    dep_name = link.get_text(strip=True)
                    mod_url = f"{BASE_MOD_URL}{BASE_FACTORIO_MOD_URL}/{dep_name}"
                    required_mods.append((dep_name, mod_url))

            return required_mods
        except Exception as e:
            self.log_info(f"Could not fetch dependencies for {mod_name}: {e}\n")
            return []

    def download_file(self, url: str, file_path: str, file_name: str):
        entry = self.app.downloader_frame.add_download(file_name)
        entry.progress_bar.set(0)

        def _download():
            max_retries = 3
            retry_delay = 2

            for attempt in range(1, max_retries + 1):
                try:
                    response = requests.get(url, stream=True, timeout=30)
                    response.raise_for_status()

                    total_size = int(response.headers.get("content-length", 0))
                    min_chunk = 64 * 1024
                    max_chunk = 4 * 1024 * 1024
                    block_size = max(min_chunk, min(total_size // 100, max_chunk))
                    progress = 0

                    if not total_size:
                        entry.progress_bar.after(
                            0, entry.progress_bar.configure, {"mode": "indeterminate"}
                        )

                    with open(file_path, "wb") as file:
                        start_time = time.time()
                        last_update = start_time

                        for chunk in response.iter_content(chunk_size=block_size):
                            if not chunk:
                                continue

                            file.write(chunk)
                            progress += len(chunk)

                            percentage = progress / total_size if total_size else 0
                            now = time.time()

                            if now - last_update >= 0.2:
                                elapsed = now - start_time
                                speed = ((progress / 1024 / 1024) / elapsed if elapsed > 0 else 0.0)
                                downloaded_mb = progress / 1024 / 1024
                                total_mb = total_size / 1024 / 1024 if total_size else 0

                                entry.progress_bar.after(
                                    0,
                                    lambda p=percentage, d=downloaded_mb, t=total_mb, s=speed: entry.update_progress(
                                        p, d, t, s
                                    ),
                                )
                                last_update = now

                    entry.text_label.after(0, entry.mark_complete)
                    self.log_info(f"Downloaded: {file_path.replace('\\', '/')}.\n")
                    break

                except Exception as e:
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    if attempt < max_retries:
                        entry.text_label.after(
                            0, lambda x=attempt: entry.mark_retrying(x, max_retries)
                        )
                        self.log_info(f"Error downloading {file_path} (attempt {attempt}): {e}\nRetrying...")
                        time.sleep(retry_delay)
                    else:
                        entry.text_label.after(0, lambda: entry.mark_failed(str(e)))
                        self.log_info(f"Failed to download {file_path} after {max_retries} attempts: {e}\n")

        t = Thread(target=_download, daemon=True)
        t.start()
        self.download_threads.append(t)

    def download_mod_with_dependencies(self, mod_url: str, download_path: str):
        mod_name_display = mod_url.split("/")[-1]
        self.app.progressbar.stop()
        self.app.progress_file.after(
            0,
            lambda: self.app.progress_file.configure(text=f"Analyzing mod {mod_name_display}"),
        )

        self.app.progressbar.configure(mode="indeterminate")
        self.app.progressbar.start()

        try:
            soup = self.get_page_source(mod_url)
            mod_name = self.get_mod_name(soup)
            latest_version = self.get_latest_version(soup)

            if not mod_name or not latest_version:
                self.log_info(f"Error: Could not get mod info for {mod_url}. Skipping!\n")
                return

            if mod_name in ("space-age",):
                self.log_info(f"Skipping reserved dependency {mod_name}. Download manually if needed.\n")
                return

            # --- WYŚWIETLENIE INFORMACJI PRZED POBRANIEM ---
            self.log_info(f"[INFO] Mod: {mod_name} | Version for Factorio {self.target_factorio_version}: {latest_version}\n")
            self.analyzed_mods.add(mod_url)

            # Pobieramy i logujemy zależności przed pobraniem pliku głównego
            self.log_info(f"Loading dependencies for {mod_name}...\n")
            dependencies = self.get_required_dependencies(mod_name)
            
            if dependencies:
                dep_names = ", ".join([dep_name for dep_name, _ in dependencies])
                self.log_info(f"[DEPENDENCIES] Found for {mod_name}: {dep_names}\n")
            else:
                self.log_info(f"[DEPENDENCIES] No dependencies found for {mod_name}.\n")
            # -----------------------------------------------

            download_url = (
                f"{BASE_DOWNLOAD_URL}/{mod_name}/{latest_version}.zip"
                f"?anticache={generate_anticache()}"
            )
            file_name = f"{mod_name}_{latest_version}.zip"
            file_path = os.path.join(download_path, file_name)

            os.makedirs(download_path, exist_ok=True)

            if file_name not in self.downloaded_mods:
                self.log_info(f"Starting download for {file_name}.\n")
                self.downloaded_mods.add(file_name)
                self.download_file(download_url, file_path, file_name)
            else:
                self.log_info(f"Mod already downloaded {file_name}. Skipping!\n")

            # Przetwarzanie pobranych zależności
            for dep_name, dep_url in dependencies:
                if dep_name in self.downloaded_mods or dep_url in self.analyzed_mods:
                    continue

                self.log_info(f"Analyzing dependency {dep_name} of {mod_name}\n")
                self.download_mod_with_dependencies(dep_url, download_path)

        except Exception as e:
            self.log_info(f"Error processing mod: {str(e).split('\n')[0]}\n")

    def log_info(self, info: str):
        self.app.textbox.configure(state="normal")
        self.app.textbox.insert("end", info)
        self.app.textbox.yview("end")
        self.app.textbox.configure(state="disabled")