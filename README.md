# Meraki Multi-Org Switch Stack Auditor

This Python tool provides a comprehensive health audit of Cisco Meraki Switch Stacks across one or multiple organizations. It scans for stack membership status and physical stack port connectivity, providing a color-coded summary in the terminal.

> [!CAUTION]
> **⚠️ USE AT YOUR OWN RISK**  
> This script is provided "as is" without warranty of any kind. The author is not responsible for any issues, downtime, or data loss caused by the use of this script. Always test in a lab environment before running against production networks.

## 🚀 Features

- **Multi-Org Support**: Audit all organizations accessible via your API key or a specific list of Organization IDs.
- **Bulk Processing**: Uses Meraki's bulk API endpoints for efficient data retrieval.
- **Health Categorization**: Automatically classifies stacks into four health states (Healthy, Stack Port Issues, Partial Offline, or Fully Offline).
- **Real-time Progress**: Includes a progress bar and detailed logging options for transparency during long-running scans.
- **Resilient**: Gracefully handles API errors or incorrect Organization IDs by skipping them and moving to the next target.

## 📋 Prerequisites

- **Python 3.6+**
- **Meraki Python Library**: 
  ```bash
  pip install meraki
  ```
- **Meraki API Key**: Ensure you have an API key with appropriate permissions (Read-only is sufficient).

## ⚙️ Configuration

1.  **Environment Variable**: The script looks for an environment variable named `MK_CSM_KEY` for your API key.
    ```bash
    # Linux/macOS
    export MK_CSM_KEY='your_api_key_here'
    
    # Windows (Command Prompt)
    set MK_CSM_KEY=your_api_key_here
    ```
2.  **Targeting Organizations**: Open the script and locate the `TARGET_ORG_IDS` list:
    -   `TARGET_ORG_IDS = []`: The script will audit **all** organizations.
    -   `TARGET_ORG_IDS = ["12345", "67890"]`: The script will **only** audit these specific IDs.
3.  **Logging Levels**:
    -   `SHOW_NETWORK_LOGS`: Set to `True` to see a summary after each network is scanned.
    -   `SHOW_DETAILED_LOGS`: Set to `True` to see individual switch and port status during the scan.

## 🏃 Usage

Run the script from your terminal:

```bash
python meraki_stack_audit.py
```

## 📊 Health Categories Explained

The script categorizes stacks based on the following logic:

| Icon | Category | Description |
| :--- | :--- | :--- |
| 🔴 | **All Offline** | Every member of the stack is currently offline or dormant. |
| 🟡 | **Partial Offline** | A "split-brain" or degraded state where some members are online and others are offline. |
| 🟠 | **Online Issue** | All switches are online, but at least one physical stack cable/port is disconnected. |
| 🟢 | **Fully Healthy** | All members are online and all stack ports are reporting a "Connected" status. |

## 🛠️ Error Handling

- **Invalid IDs**: If an Organization ID in the `TARGET_ORG_IDS` list is invalid or the API key lacks permissions for it, the script will print a warning and continue to the next organization.
- **Rate Limiting**: API rate limiting is handled automatically by the Meraki SDK's built-in retry mechanism.

## 📝 License & Disclaimer

This project is intended for internal network auditing and administrative use. 

**Disclaimer:** Use at your own risk. The software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement.

***
*For more information on the Meraki API, visit the [Meraki Developer Hub](https://developer.cisco.com/meraki/).*
