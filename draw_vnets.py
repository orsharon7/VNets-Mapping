import csv
import logging
from azure.identity import AzureCliCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from azure.core.exceptions import AzureError, ClientAuthenticationError
from graphviz import Digraph
import os

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

def get_all_subscriptions():
    try:
        logging.info("Fetching all subscriptions...")
        credential = AzureCliCredential()
        subscription_client = SubscriptionClient(credential)
        subscriptions = [sub.subscription_id for sub in subscription_client.subscriptions.list()]
        return subscriptions
    except AzureError as e:
        logging.error(f"Failed to get subscriptions: {e}")
        return []

def list_vnets_and_peerings(subscription_id, credential):
    try:
        network_client = NetworkManagementClient(credential, subscription_id)
        vnet_list = []
        vnet_peering_list = []

        for vnet in network_client.virtual_networks.list_all():
            vnet_info = {
                "CIDR": ", ".join(vnet.address_space.address_prefixes),
                "VNET": vnet.name,
                "ResourceGroup": vnet.id.split('/')[4],
                "SubscriptionId": subscription_id
            }
            vnet_list.append(vnet_info)

            # Process peerings
            peerings = network_client.virtual_network_peerings.list(vnet_info["ResourceGroup"], vnet.name)
            for peering in peerings:
                # Get the remote VNet details
                remote_vnet_id = peering.remote_virtual_network.id
                remote_vnet = network_client.virtual_networks.get(
                    resource_group_name=remote_vnet_id.split('/')[4],
                    virtual_network_name=remote_vnet_id.split('/')[-1]
                )
                remote_vnet_cidr = ", ".join(remote_vnet.address_space.address_prefixes)

                vnet_peering_list.append({
                    "SourceVNet": vnet.name,
                    "SourceCIDR": vnet_info["CIDR"],
                    "SourceResourceGroup": vnet_info["ResourceGroup"],
                    "TargetVNet": remote_vnet.name,
                    "TargetCIDR": remote_vnet_cidr,
                    "PeeringState": peering.peering_state
                })
        return vnet_list, vnet_peering_list
    except ClientAuthenticationError:
        logging.warning(f"No access to subscription {subscription_id}.")
        return [], []
    except AzureError as e:
        logging.error(f"Failed to list VNets for subscription {subscription_id}: {e}")
        return [], []

def write_to_csv(data, filename, fieldnames):
    try:
        with open(filename, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except IOError as e:
        logging.error(f"Failed to write to CSV file {filename}: {e}")

def visualize_peerings(peerings):
    dot = Digraph(comment="VNet Peering Diagram")
    dot.attr(size='11,8.5', ratio='fill')  # Adjust size and ratio for better visualization
    dot.attr(dpi='1000')  # Set DPI to a lower value to reduce pixelation
    colors = ["red", "blue", "green", "yellow", "purple", "orange", "brown", "pink", "gray", "cyan"]
    color_index = 0

    for peering in peerings:
        source = f"{peering['SourceVNet']} ({peering['SourceCIDR']})"
        target = f"{peering['TargetVNet']} ({peering['TargetCIDR']})"
        dot.edge(source, target, label=peering["PeeringState"], color=colors[color_index % len(colors)])
        color_index += 1

    dot.render("vnet_peering_diagram", format="png", cleanup=True)
    logging.info("Diagram saved as vnet_peering_diagram.png")

def main():
    credential = AzureCliCredential()
    subscriptions = get_all_subscriptions()
    all_vnets = []
    all_peerings = []

    for sub in subscriptions:
        vnets, peerings = list_vnets_and_peerings(sub, credential)
        all_vnets.extend(vnets)
        all_peerings.extend(peerings)

    write_to_csv(all_vnets, "all_vnets.csv", ["CIDR", "VNET", "ResourceGroup", "SubscriptionId"])
    write_to_csv(all_peerings, "vnet_peerings.csv", ["SourceVNet", "SourceCIDR", "SourceResourceGroup", "TargetVNet", "TargetCIDR", "PeeringState"])
    visualize_peerings(all_peerings)

if __name__ == "__main__":
    main()