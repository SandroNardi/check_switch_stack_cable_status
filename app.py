import os
import meraki
import sys
from collections import Counter

# --- Configuration ---
API_KEY = os.environ.get("MK_CSM_KEY") #read only API KEY access is sufficent

# --- Organization Filter ---
# Paste your Organization IDs here as strings, e.g., ["12345", "67890"]
# If the list is empty [], the script will perform the audit on ALL accessible organizations.
TARGET_ORG_IDS = ["org id 1","org id 2"] #list target ORG ID's otr leave it empty for all the accessible orgs| required

# --- Output Control Variables ---
SHOW_NETWORK_LOGS = True 
SHOW_DETAILED_LOGS = True 

# Initialize Dashboard
dashboard = meraki.DashboardAPI(API_KEY, suppress_logging=True)

# ANSI Color Codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
RESET = '\033[0m'

def get_status_emoji(status):
    status_map = {"online": "🟢", "alerting": "🟡", "offline": "🔴", "dormant": "⚪"}
    return status_map.get(status, "❓")

def get_port_status_colored(status):
    if status.lower() == "connected":
        return f"{GREEN}{status}{RESET}"
    elif status.lower() == "disconnected":
        return f"{RED}{status}{RESET}"
    return status

def terminal_log(message):
    """Clears the progress bar line and prints a message to the terminal."""
    sys.stdout.write('\r\033[K') 
    print(message)

def update_progress(iteration, total, prefix='', length=40):
    """Updates the progress bar in-place on the bottom line."""
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r\033[K{prefix} Progress: |{bar}| {percent}%')
    sys.stdout.flush()

def run_multi_org_audit():
    all_org_reports = {}
    
    # Define categories for reuse
    categories_meta = [
        ("🔴", "cat1_all_offline", "All members offline or dormant"),
        ("🟡", "cat2_partial_offline", "Partial membership offline (mixed)"),
        ("🟠", "cat3_online_issue", "All online but at least one stack port disconnected"),
        ("🟢", "cat4_fully_healthy", "Fully healthy (all online & all stack ports connected)")
    ]

    try:
        # Determine which organizations to audit
        orgs_to_process = []
        if not TARGET_ORG_IDS:
            print(f"{YELLOW}No specific IDs provided. Fetching all accessible organizations...{RESET}")
            orgs_to_process = dashboard.organizations.getOrganizations()
        else:
            print(f"{YELLOW}Targeting {len(TARGET_ORG_IDS)} specific organization(s)...{RESET}")
            for org_id in TARGET_ORG_IDS:
                try:
                    org_data = dashboard.organizations.getOrganization(org_id)
                    orgs_to_process.append(org_data)
                except meraki.APIError as e:
                    print(f"{RED}⚠️ Warning: Could not access Org ID {org_id}. Skipping. (Error: {e.message}){RESET}")

        for org in orgs_to_process:
            org_id = org['id']
            org_name = org['name']
            
            all_org_reports[org_name] = {cat[1]: [] for cat in categories_meta}

            print(f"\n🚀 Auditing Organization: {BOLD}{org_name}{RESET} (ID: {org_id})")

            try:
                dev_statuses = dashboard.organizations.getOrganizationDevicesStatuses(org_id)
                status_lookup = {d['serial']: {"status": d['status'], "name": d.get('name', 'Unnamed')} for d in dev_statuses}

                all_devices = dashboard.organizations.getOrganizationDevices(org_id, total_pages='all')
                switch_counts = Counter(d['networkId'] for d in all_devices if d.get('productType') == 'switch')
                candidate_network_ids = [net_id for net_id, count in switch_counts.items() if count >= 2]
                
                if not candidate_network_ids:
                    terminal_log("  No networks found with at least 2 switches. Skipping stack audit.")
                    continue

                all_networks = dashboard.organizations.getOrganizationNetworks(org_id)
                net_name_map = {n['id']: n['name'] for n in all_networks}
                
                org_stacks_by_net = {} 
                all_stacked_serials = []

                terminal_log(f"  Checking {len(candidate_network_ids)} candidate networks for stacks...")
                for net_id in candidate_network_ids:
                    stacks = dashboard.switch.getNetworkSwitchStacks(net_id)
                    if stacks:
                        org_stacks_by_net[net_id] = stacks
                        for s in stacks:
                            all_stacked_serials.extend(s.get('serials', []))

                if not all_stacked_serials:
                    terminal_log("  No switch stacks detected in candidate networks.")
                    continue

                # Bulk Fetch Port Data
                raw_configs = dashboard.switch.getOrganizationSwitchPortsBySwitch(org_id, total_pages='all', serials=all_stacked_serials)
                config_lookup = {item['serial']: item['ports'] for item in raw_configs}

                raw_statuses_response = dashboard.switch.getOrganizationSwitchPortsStatusesBySwitch(org_id, total_pages='all', serials=all_stacked_serials)
                status_lookup_ports = {item['serial']: {p['portId']: p['status'] for p in item['ports']} for item in raw_statuses_response.get('items', [])}

                # Process Networks and Stacks
                total_nets = len(org_stacks_by_net)
                for i, (net_id, stacks) in enumerate(org_stacks_by_net.items(), 1):
                    net_name = net_name_map.get(net_id, "Unknown")
                    update_progress(i, total_nets, prefix=f"  [{org_name}]")
                    
                    network_report = {cat[1]: [] for cat in categories_meta}

                    for stack in stacks:
                        stack_name = stack.get('name', 'Unnamed Stack')
                        serials = stack.get('serials', [])
                        num_members = len(serials)

                        online_count = 0
                        offline_count = 0
                        has_disconnected_stack_port = False

                        if SHOW_DETAILED_LOGS:
                            terminal_log(f"\n    {BOLD}Processing Stack: {stack_name} ({num_members} members){RESET}")

                        for serial in serials:
                            info = status_lookup.get(serial, {"status": "unknown", "name": "Unknown"})
                            sw_status = info['status']
                            
                            if SHOW_DETAILED_LOGS:
                                terminal_log(f"      {get_status_emoji(sw_status)} Switch: {info['name']} ({serial}) - {sw_status.upper()}")

                            if sw_status in ['online', 'alerting']:
                                online_count += 1
                                ports_config = config_lookup.get(serial, [])
                                port_status_map = status_lookup_ports.get(serial, {})

                                for port in ports_config:
                                    if port.get('type') == 'stack':
                                        raw_status = port_status_map.get(port['portId'], "Unknown")
                                        if raw_status.lower() == "disconnected":
                                            has_disconnected_stack_port = True
                                        if SHOW_DETAILED_LOGS:
                                            terminal_log(f"        - Port {port['portId']}: {get_port_status_colored(raw_status)}")
                            else:
                                offline_count += 1

                        # Categorization
                        stack_entry = f"{stack_name} ({num_members} members)"
                        cat_key = ""
                        if online_count == 0: cat_key = "cat1_all_offline"
                        elif offline_count > 0 and online_count > 0: cat_key = "cat2_partial_offline"
                        elif online_count == len(serials) and has_disconnected_stack_port: cat_key = "cat3_online_issue"
                        else: cat_key = "cat4_fully_healthy"

                        network_report[cat_key].append(stack_entry)
                        all_org_reports[org_name][cat_key].append(f"{stack_name} [{net_name}] ({num_members} members)")

                    if SHOW_NETWORK_LOGS:
                        terminal_log(f"\n    {BOLD}NETWORK: {net_name}{RESET}")
                        terminal_log(f"    {'-' * (len(net_name) + 13)}")
                        for emoji, key, description in categories_meta:
                            count = len(network_report[key])
                            terminal_log(f"    {emoji} ({count}) {description}")
                            for item in network_report[key]:
                                terminal_log(f"      - {item}")
                
                sys.stdout.write('\r\033[K') 
                print(f"  {GREEN}✓ Audit complete for {org_name}{RESET}")

            except meraki.APIError as e:
                terminal_log(f"  {RED}Skipping Org {org_name}: {e}{RESET}")

    except meraki.APIError as e:
        print(f"An error occurred: {e}")

    # --- FINAL MULTI-ORG SUMMARY REPORT ---
    print(f"\n\n{'='*80}")
    print(f"{BOLD}MULTI-ORGANIZATION STACK HEALTH SUMMARY REPORT{RESET}")
    print(f"{'='*80}")

    for org_name, report in all_org_reports.items():
        print(f"\n{BOLD}ORGANIZATION: {org_name}{RESET}")
        print("-" * (len(org_name) + 14))
        
        total_stacks_in_org = sum(len(report[key]) for _, key, _ in categories_meta)

        if total_stacks_in_org == 0:
            print(f"  No switch stacks found in this organization.")
        else:
            for emoji, key, description in categories_meta:
                count = len(report[key])
                print(f"{emoji} ({count}) {description}")
                if count > 0:
                    for item in report[key]:
                        print(f"  - {item}")

    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    run_multi_org_audit()