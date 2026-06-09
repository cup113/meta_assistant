python -m nuitka --standalone --windows-console-mode=disable --windows-icon-from-ico=assistant.ico --include-data-files=assistant.ico=./assistant.ico --output-dir=dist --enable-plugin=tk-inter --assume-yes-for-downloads meta_assistant
echo dist\meta_assistant.dist\ is ready. Run `iscc /DAPP_VERSION="dev" installer.iss` to create a setup.
