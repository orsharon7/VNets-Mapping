```sh
python -m venv venv
source venv/bin/activate 
pip install -r requirements.txt
export AZURE_LOG_LEVEL=WARNING
```

### Graphviz Installation:
- **Ubuntu:** `sudo apt-get install graphviz`
- **macOS:** `brew install graphviz`
- **Windows:** Download and install from [Graphviz Download Page](https://graphviz.org/download/).

### Outputs
1. **CSV Files:**
    - `all_vnets.csv`: Contains VNet details.
    - `vnet_peerings.csv`: Contains VNet peering details.
2. **Diagram:**
    - `vnet_peering_diagram.png`: Visual representation of VNets and their peerings.

### Run
```sh
python draw_vnets.py
```