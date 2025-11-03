#!/bin/bash
# Setup script for git repository management of Jupyter notebooks

set -e

echo "Setting up git repository for Jupyter notebook management..."
echo ""

# Check if nbstripout is installed
if ! command -v nbstripout &> /dev/null; then
    echo "Installing nbstripout..."
    pip install nbstripout
else
    echo "nbstripout is already installed"
fi

# Install git filter
echo ""
echo "Installing nbstripout git filter..."
nbstripout --install

# Verify installation
echo ""
echo "Checking git filter configuration..."
git config --get filter.nbstripout.clean && echo "✓ Git filter configured successfully" || echo "✗ Git filter configuration failed"

# Clean existing notebooks
echo ""
echo "Cleaning existing notebooks..."
find . -name "*.ipynb" -exec nbstripout {} \;
echo "✓ Notebooks cleaned"

echo ""
echo "Setup complete!"
echo ""
echo "Your notebooks will now automatically have outputs stripped before commits."
echo "To manually clean notebooks, run: nbstripout SNOWPACKforPatrollers.ipynb"

