#!/usr/bin/env bash
# Build & test script for Flash Sale Inventory Reservation System
# Requires: JDK 21+ on PATH
set -euo pipefail

OUT_DIR="out"
MAIN_SRC="src/main/java"
TEST_SRC="src/test/java"

echo "=== Compiling main sources ==="
mkdir -p "$OUT_DIR/classes"
find "$MAIN_SRC" -name "*.java" > "$OUT_DIR/sources.txt"
javac --release 21 -d "$OUT_DIR/classes" @"$OUT_DIR/sources.txt"
echo "Main sources compiled OK."

echo "=== Compiling test sources ==="
mkdir -p "$OUT_DIR/test-classes"
find "$TEST_SRC" -name "*.java" > "$OUT_DIR/test-sources.txt"
javac --release 21 -cp "$OUT_DIR/classes" -d "$OUT_DIR/test-classes" @"$OUT_DIR/test-sources.txt"
echo "Test sources compiled OK."

echo "=== Running tests ==="
java -ea -cp "$OUT_DIR/classes:$OUT_DIR/test-classes" com.flashsale.TestRunner

echo "=== Building JAR ==="
jar --create --file "$OUT_DIR/flash-sale.jar" \
    --main-class=com.flashsale.cli.ReservationCli \
    -C "$OUT_DIR/classes" .
echo "JAR built: $OUT_DIR/flash-sale.jar"

echo ""
echo "=== BUILD SUCCESS ==="
echo "Run:  java -jar $OUT_DIR/flash-sale.jar demo"
echo "Test: java -ea -cp $OUT_DIR/classes:$OUT_DIR/test-classes com.flashsale.TestRunner"