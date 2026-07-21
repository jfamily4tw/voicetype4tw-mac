#!/bin/bash
set -e

echo "🛡️  Pre-build guard: MLX version pin..."
python3.12 scripts/pre_build_check.py || {
    echo "❌ Pre-build check failed (see above). Aborting before py2app."
    exit 1
}

echo "🧹 Cleaning old build..."
rm -rf build dist/dmg_staging dist/*.app dist/VoiceType4TW-Mac.app 2>/dev/null || true
mkdir -p dist

echo "🍎 Building Apple Foundation Models helper..."
swiftc -parse-as-library helpers/apple_local_llm.swift -o helpers/apple_local_llm

echo "🔧 Building .app with py2app..."
python3.12 setup.py py2app

echo "🔗 Applying post-build fixes (OpenSSL rpath, MLX libraries)..."
python3.12 post_build_fix.py "dist/嘴炮輸入法.app" || {
    echo "❌ Post-build fix failed!"
    exit 1
}

echo "📦 Packaging DMG..."
./pack_dmg.sh

echo "✅ All Done!"
