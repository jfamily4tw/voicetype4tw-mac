#!/bin/bash
set -e

echo "🧹 Cleaning old build..."
rm -rf build dist/dmg_staging dist/*.app dist/VoiceType4TW-Mac.app 2>/dev/null || true
mkdir -p dist

echo "🔧 Building .app with py2app..."
python3.12 setup.py py2app

echo "📦 Packaging DMG..."
./pack_dmg.sh

echo "✅ All Done!"
