import csv
import logging
import argparse
from azure.identity import AzureCliCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from azure.core.exceptions import AzureError, ClientAuthenticationError
from graphviz import Digraph

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('azure').setLevel(logging.WARNING)  # Suppress detailed API call logs

def get_all_subscriptions():
    try:
        logging.info("Fetching all subscriptions...")
        credential = AzureCliCredential()
        subscription_client = SubscriptionClient(credential)
        subscriptions = [sub.subscription_id for sub in subscription_client.subscriptions.list()]
        logging.info(f"Found {len(subscriptions)} subscriptions.")
        return subscriptions
    except AzureError as e:
        logging.error(f"Failed to get subscriptions: {e}")
        return []

def list_vnets(subscription_id, credential):
    try:
        logging.info(f"Processing subscription {subscription_id}...")
        network_client = NetworkManagementClient(credential, subscription_id)
        vnet_list = []
        for vnet in network_client.virtual_networks.list_all():
            peered_vnets = []
            peerings = network_client.virtual_network_peerings.list(vnet.id.split('/')[4], vnet.name)
            for peering in peerings:
                peered_vnets.append(peering.remote_virtual_network.id)
            for address_space in vnet.address_space.address_prefixes:
                vnet_list.append({
                    "CIDR": address_space,
                    "VNET": vnet.name,
                    "ResourceGroup": vnet.id.split('/')[4],
                    "SubscriptionId": subscription_id,
                    "PeeredVNets": peered_vnets
                })
        logging.info(f"Found {len(vnet_list)} VNets in subscription {subscription_id}.")
        return vnet_list
    except ClientAuthenticationError:
        logging.warning(f"No access to subscription {subscription_id}.")
        print(f"No read access to VNets | RG | Subscription: {subscription_id}")
        return []
    except AzureError as e:
        logging.error(f"Failed to list VNets for subscription {subscription_id}: {e}")
        return []

def write_to_csv(data, filename):
    try:
        with open(filename, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["CIDR", "VNET", "ResourceGroup", "SubscriptionId", "PeeredVNets"])
            writer.writeheader()
            for row in data:
                row["PeeredVNets"] = ";".join(row["PeeredVNets"])  # Convert list to semicolon-separated string
                writer.writerow(row)
        logging.info(f"Data written to {filename}")
    except IOError as e:
        logging.error(f"Failed to write to CSV file {filename}: {e}")

def main():
    parser = argparse.ArgumentParser(description="VNet CIDR inspection and visualization script.")
    parser.add_argument('--subscription-ids', nargs='+', help="List of subscription IDs to review.")
    args = parser.parse_args()

    credential = AzureCliCredential()
    if args.subscription_ids:
        subscriptions = args.subscription_ids
        logging.info(f"Reviewing specified subscriptions: {subscriptions}")
    else:
        subscriptions = get_all_subscriptions()

    all_vnets = []
    for sub in subscriptions:
        vnets = list_vnets(sub, credential)
        all_vnets.extend(vnets)

    # Write all VNets to CSV
    logging.info("Writing all VNets to CSV...")
    write_to_csv(all_vnets, "all_vnets.csv")

    logging.info("Script execution completed.")

if __name__ == "__main__":
    main()