#!/bin/bash

tree -I "node_modules|.git|__pycache__|.venv" > docs/project_tree.txt

echo "Project tree updated!"
