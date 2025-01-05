import csv
import logging
from azure.identity import AzureCliCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from azure.core.exceptions import AzureError, ClientAuthenticationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            for address_space in vnet.address_space.address_prefixes:
                vnet_list.append({
                    "CIDR": address_space,
                    "VNET": vnet.name,
                    "ResourceGroup": vnet.id.split('/')[4],
                    "SubscriptionId": subscription_id
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
            writer = csv.DictWriter(file, fieldnames=["CIDR", "VNET", "ResourceGroup", "SubscriptionId"])
            writer.writeheader()
            writer.writerows(data)
        logging.info(f"Data written to {filename}")
    except IOError as e:
        logging.error(f"Failed to write to CSV file {filename}: {e}")

def identify_collisions(data):
    logging.info("Identifying CIDR collisions...")
    cidr_map = {}
    for item in data:
        cidr = item["CIDR"]
        if cidr not in cidr_map:
            cidr_map[cidr] = []
        cidr_map[cidr].append(item)
    
    collisions = []
    for cidr, items in cidr_map.items():
        if len(items) > 1:
            collisions.extend(items)
    logging.info(f"Found {len(collisions)} collisions.")
    return sorted(collisions, key=lambda x: x["CIDR"])

def main():
    logging.info("Starting the VNet CIDR inspection script...")
    credential = AzureCliCredential()
    subscriptions = get_all_subscriptions()
    all_vnets = []

    for sub in subscriptions:
        vnets = list_vnets(sub, credential)
        all_vnets.extend(vnets)

    # Write all VNets to CSV
    logging.info("Writing all VNets to CSV...")
    write_to_csv(all_vnets, "all_vnets.csv")

    # Identify collisions
    collisions = identify_collisions(all_vnets)

    # Write collisions to CSV
    logging.info("Writing collisions to CSV...")
    write_to_csv(collisions, "colliding_vnets.csv")
    logging.info("Script execution completed.")

if __name__ == "__main__":
    main()