#!/usr/bin/env bash

#NOTE: Auto-Update will only be attempted if a versioned form of the tinker-access-client is already installed
pip_package_name="tinker-access-client"
${pip_package_name} --version >/dev/null 2>/dev/null
if [ $? -eq 0 ]; then
    restart_required=`pip install --upgrade ${pip_package_name}`
    if [[ ${restart_required} == *"Successfully installed ${pip_package_name}"* ]]; then
        ${pip_package_name} restart
    fi
fi