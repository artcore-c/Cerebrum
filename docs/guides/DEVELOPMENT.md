# Cerebrum/docs/guides/DEVELOPMENT.md

## Setup on Mac

1. Clone/create project
2. Edit files in VS Code
3. Sync to CM4/VPS when ready

## Sync Workflow

```bash
# Sync CM4 changes
./scripts/sync_to_cm4.sh

# Sync VPS changes
./scripts/sync_to_vps.sh
```

## Testing

### Test CM4
```bash
ssh kali@100.75.37.26
cd /opt/cerebrum-pi
./test.sh
```

### Test VPS
```bash
ssh unicorn1@100.78.22.113
cd ~/cerebrum-backend
./test.sh
```

## File Organization

- **cm4/** - Edit CM4 code here
- **vps/** - Edit VPS code here
- **shared/** - Models, knowledge base
- **docs/** - Documentation

## Adding New Features

1. Edit code on Mac
2. Test locally if possible
3. Sync to target system
4. Test on real hardware
5. Iterate
