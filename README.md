
This release contains the full source code for the updated Factorio Mod Downloader. There is pre-built `.exe` file included in this release, you can easily download and run yourself.

# 🎮 How to Use (Quick Guide for Users)

Once you run the application, follow these simple steps to download your mods:

1. **Select Game Version:** Use the new drop-down menu to choose your Factorio version (e.g., select `2.0` if you are playing Space Age).
2. **Paste Mod URL:** Go to the official Factorio mod portal, copy the link (URL) of the mod you want, and paste it into the application.
3. **Select Download Folder:** Choose the folder where you want to save the downloaded files (usually your Factorio `mods` directory).
4. **Click Download:** Click the download button. The application will automatically analyze the mod, look for all required dependencies, and download everything in the background.
5. **Done!** A pop-up dialog will appear once all files are successfully downloaded and ready.


# 🚀 What's New:
* **Game Version Selector:** Manually choose your target Factorio version (full support for **Factorio 2.0+ Space Age**).
* **Dependency Fixes:** Resolved version conflicts to allow smooth operations on modern Python setups.

---

# 🛠️ For Developers (How to install, run & build)

Follow these steps to setup the project locally on your machine:

## 1. Prerequisites
Make sure you have **Python** installed on your system.

## 2. Clone or Download the Repository
* Click the green **Code** button on the main repository page and select **Download ZIP**, then extract it.
* *Or* clone it via Git terminal (replace `YOUR-USERNAME` with your actual GitHub name):
  ```bash
  git clone [https://github.com/YOUR-USERNAME/factorio-mod-downloader.git](https://github.com/YOUR-USERNAME/factorio-mod-downloader.git)
  cd factorio-mod-downloader
3. Install Dependencies & Run
Install all required libraries using standard Python pip and run the application directly from the source code:

```bash
  pip install customtkinter ctkmessagebox pillow requests beautifulsoup4 selenium chromedriver-autoinstaller
  python src/factorio_mod_downloader/__main__.py
```
4. How to Build the Standalone .exe (Using PyInstaller)
If you want to compile this source code into a single, executable file (.exe) with the application icon included, install PyInstaller and run the compilation command:

```
# 1. Install PyInstaller

    pip install pyinstaller

# 2. Build the executable

pyinstaller --noconfirm --onedir --windowed --add-data "src/factorio_mod_downloader/assets;factorio_mod_downloader/assets" --icon="src/factorio_mod_downloader/assets/factorio_downloader.ico" "src/factorio_mod_downloader/__main__.py" --name "factorio-mod-downloader"
```
Once the build process is complete, you will find your standalone application in the following directory:

📁 dist/factorio-mod-downloader/factorio-mod-downloader.exe

Note: All core application mechanics and design belong to the original author, Vaibhav Vikas. This is an open-source modification.
