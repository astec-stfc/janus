#!/bin/bash

# Check if an SSH key path was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <path-to-ssh-key>"
    exit 1
fi

SSH_KEY="$1"

# Check if the key file exists
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key file not found: $SSH_KEY"
    exit 1
fi

# detect whether script is sourced
sourced=0
if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  sourced=1
fi

# helper to print export lines (for eval "$(./configure.sh ...)")
print_exports() {
  printf 'export SSH_AUTH_SOCK=%q;\n' "$SSH_AUTH_SOCK"
  printf 'export SSH_AGENT_PID=%q;\n' "$SSH_AGENT_PID"
}

if [ -n "$SSH_AUTH_SOCK" ] && ssh-add -l >/dev/null 2>&1; then
  ssh-add "$SSH_KEY" >/dev/null 2>&1 || true
  if [ $sourced -eq 1 ]; then
    echo "SSH agent already running; key added (if not present)."
    return 0
  else
    print_exports
    exit 0
  fi
fi

# start a new agent and add the key
AGENT_OUT=$(ssh-agent -s)
eval "$AGENT_OUT"
ssh-add "$SSH_KEY" >/dev/null 2>&1

if [ $sourced -eq 1 ]; then
  echo "SSH agent started and key added successfully"
  return 0
else
  print_exports
  exit 0
fi
