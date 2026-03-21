#!/bin/bash

# Configuration
APP_NAME="嘴炮輸入法"
VERSION="2.9.7-Coffee-Edition"
DMG_NAME="${APP_NAME}_v${VERSION}_macOS.dmg"
STAGING_DIR="dist/dmg_staging"
VOL_NAME="${APP_NAME}"

echo "[DMG] Preparing staging directory..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

# Copy files
cp -r "dist/${APP_NAME}.app" "$STAGING_DIR/"

# v2.8.4: Ensure instruction file is included with correct name
if [ -f "安裝說明.md" ]; then
    cp "安裝說明.md" "$STAGING_DIR/"
elif [ -f "首次開啟必看_解除損毀警告.md" ]; then
    cp "首次開啟必看_解除損毀警告.md" "$STAGING_DIR/安裝說明.md"
elif [ -f "dist/INSTALL_MAC.md" ]; then
    cp "dist/INSTALL_MAC.md" "$STAGING_DIR/安裝說明.md"
fi

ln -s /Applications "$STAGING_DIR/Applications"

# Set up background and Volume Icon
mkdir "$STAGING_DIR/.background"
# v2.8.4: Create Retina-compatible background TIFF
if [ -f "assets/DMG-BG-2x.jpg" ]; then
    tiffutil -cathidpicheck "assets/DMG-BG.jpg" "assets/DMG-BG-2x.jpg" -out "$STAGING_DIR/.background/background.tiff"
else
    cp "assets/DMG-BG.jpg" "$STAGING_DIR/.background/background.jpg"
fi

# v2.8.4: Handle Volume Icon (DMG-box.png)
if [ -f "assets/DMG-box.png" ]; then
    echo "[DMG] Generating Volume Icon from DMG-box.png..."
    mkdir -p assets/dmg_icon.iconset
    sips -z 512 512 assets/DMG-box.png --out assets/dmg_icon.iconset/icon_512x512.png
    sips -z 1024 1024 assets/DMG-box.png --out assets/dmg_icon.iconset/icon_512x512@2x.png
    iconutil -c icns assets/dmg_icon.iconset -o "$STAGING_DIR/.VolumeIcon.icns"
    rm -rf assets/dmg_icon.iconset
fi

# v2.8.19: Apply dylib fixes to the STAGING app bundle
echo "[DMG] Applying post-build bundle fixes to staging area..."
python3.12 post_build_fix.py "$STAGING_DIR/${APP_NAME}.app"

echo "[DMG] Creating initial disk image..."
TEMP_DMG="dist/pack_temp.dmg"
rm -f "$TEMP_DMG"
hdiutil create -srcfolder "$STAGING_DIR" -volname "$VOL_NAME" -fs HFS+ -fsargs "-c c=64,a=16,e=16" -format UDRW "$TEMP_DMG"

echo "[DMG] Mounting disk image for layout..."
MOUNT_DIR=$(hdiutil attach -readwrite -noverify "$TEMP_DMG" | grep "/Volumes/${VOL_NAME}" | awk '{print $3}')

# Wait for mount
sleep 2

echo "[DMG] Applying AppleScript layout (Size: 640x400)..."
osascript <<APPLESCRIPT
tell application "Finder"
    tell disk "$VOL_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {400, 100, 1040, 540} 
        set viewOptions to the icon view options of container window
        set icon size of viewOptions to 100
        set arrangement of viewOptions to not arranged
        
        if exists file ".background:background.tiff" then
            set background picture of viewOptions to file ".background:background.tiff"
        else
            set background picture of viewOptions to file ".background:background.jpg"
        end if
        
        -- Positions
        set position of item "$APP_NAME.app" to {470, 121}
        set position of item "Applications" to {154, 145}
        set position of item "安裝說明.md" to {318, 260}
        
        close
        update without registering applications
        delay 2
    end tell
end tell
APPLESCRIPT

# v2.8.4: Volume Icon and flags
if [ -f "$MOUNT_DIR/.VolumeIcon.icns" ]; then
    echo "[DMG] Finalizing Volume Icon flags..."
    SetFile -a C "$MOUNT_DIR"
    SetFile -a V "$MOUNT_DIR/.VolumeIcon.icns"
fi

echo "[DMG] Finalizing disk image..."
sleep 5
hdiutil detach "$MOUNT_DIR" || hdiutil detach "$MOUNT_DIR" -force
sleep 2

rm -f "dist/$DMG_NAME"
hdiutil convert "$TEMP_DMG" -format UDZO -imagekey zlib-level=9 -o "dist/$DMG_NAME"
rm -f "$TEMP_DMG"

# v2.8.19: Sets custom icon for the DMG file itself using native python
DMG_FILE="dist/$DMG_NAME"
ICON_SOURCE="assets/DMG-box.png"
if [ -f "$ICON_SOURCE" ] && [ -f "$DMG_FILE" ]; then
    echo "[DMG] Setting custom icon to DMG file..."
    python3.12 set_dmg_icon.py "$DMG_FILE" "$ICON_SOURCE"
fi

echo "[DMG] Done: dist/$DMG_NAME"
