#!/bin/zsh
set -eu
package_dir="${0:A:h}"
exec "$package_dir/TechnocoreEasySetup.app/Contents/MacOS/TechnocoreEasySetup"
