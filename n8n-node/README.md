# n8n-nodes-sentinel-triage

Custom n8n community node for Sentinel alert triage.

## Installation

This node is designed to be installed into n8n via Docker volume or npm.

### Docker Volume Installation (Recommended for this project)

The `docker-compose.yml` mounts this directory as a volume in n8n:

```yaml
volumes:
  - ./n8n-node:/home/node/.n8n/nodes/n8n-nodes-sentinel-triage
```

Build the node first:

```bash
cd n8n-node
npm install
npm run build
```

Then start n8n with `docker compose up`. The node will appear in the node palette.

### Manual Installation

```bash
npm install
npm run build

# Copy dist to n8n custom nodes directory
cp -r dist /path/to/n8n/nodes/n8n-nodes-sentinel-triage
```

## Development

1. Edit `.ts` files in `nodes/SentinelTriage/`
2. Run `npm run build` to compile
3. Restart n8n or reload the node palette

## Project Structure

```
n8n-node/
├── nodes/
│   └── SentinelTriage/
│       ├── SentinelTriage.node.ts    # Node implementation (INodeType)
│       ├── credentials/SentinelApi.credentials.ts  # Credential type
│       ├── icon.svg                   # Node icon
│       └── README.md                  # Node usage docs
├── package.json
└── tsconfig.json
```

## API Reference

See [nodes/SentinelTriage/README.md](nodes/SentinelTriage/README.md) for detailed input/output documentation.
