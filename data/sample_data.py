"""
Sample data generation for the mail printing and stuffing database.
This module provides functions to generate and insert sample data.
"""
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Union

from faker import Faker
from src.database.connection import get_connection

# Initialize Faker with a consistent seed for reproducibility
fake = Faker()
Faker.seed(42)


def generate_sample_data(db_path: Union[str, Path], record_count: int = 5) -> None:
    """
    Generate and insert sample data into the database.
    
    Args:
        db_path: Path to the SQLite database file
        record_count: Number of records to generate for each table
    """
    conn = get_connection(db_path)
    
    try:
        # Generate and insert data for each entity type
        customer_ids = generate_and_insert_customers(conn, record_count)
        address_data = generate_and_insert_addresses(conn, customer_ids)
        material_ids = generate_and_insert_materials(conn)
        generate_and_insert_inventory(conn, material_ids)
        list_ids = generate_and_insert_mailing_lists(conn)
        list_members = generate_and_insert_list_members(conn, list_ids, customer_ids, address_data)
        campaign_ids = generate_and_insert_campaigns(conn, list_ids)
        mail_item_ids = generate_and_insert_mail_items(conn, campaign_ids, list_members)
        job_ids = generate_and_insert_print_jobs(conn)
        print_queue_entries = generate_and_insert_print_queue(conn, job_ids, mail_item_ids)
        tracking_entries = generate_and_insert_delivery_tracking(conn, mail_item_ids)
        
        # Commit all changes
        conn.commit()
        
        # Print summary
        print(f"Sample data generated successfully in {db_path}")
        print(f"Created {len(customer_ids)} customers")
        print(f"Created {len(address_data)} addresses")
        print(f"Created {len(material_ids)} materials")
        print(f"Created {len(list_ids)} mailing lists")
        print(f"Created {len(list_members)} list members")
        print(f"Created {len(campaign_ids)} campaigns")
        print(f"Created {len(mail_item_ids)} mail items")
        print(f"Created {len(job_ids)} print jobs")
        print(f"Created {len(print_queue_entries)} print queue entries")
        print(f"Created {len(tracking_entries)} delivery tracking entries")
        
    except Exception as e:
        conn.rollback()
        print(f"Error generating sample data: {str(e)}")
    finally:
        conn.close()


def generate_and_insert_customers(conn: sqlite3.Connection, count: int) -> List[int]:
    """
    Generate and insert customer data.
    
    Args:
        conn: Database connection
        count: Number of customers to generate
        
    Returns:
        List of generated customer IDs
    """
    print(f"Generating {count} customers...")
    customers = []
    
    for _ in range(count):
        customers.append({
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number()
        })
    
    # Insert customers
    cursor = conn.cursor()
    for customer in customers:
        cursor.execute(
            "INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)",
            (customer["name"], customer["email"], customer["phone"])
        )
    
    # Get customer IDs
    cursor.execute("SELECT customer_id FROM customers")
    customer_ids = [row[0] for row in cursor.fetchall()]
    
    return customer_ids


def generate_and_insert_addresses(conn: sqlite3.Connection, customer_ids: List[int]) -> List[Tuple[int, int]]:
    """
    Generate and insert address data.
    
    Args:
        conn: Database connection
        customer_ids: List of customer IDs to create addresses for
        
    Returns:
        List of tuples containing (address_id, customer_id)
    """
    addresses = []
    
    for customer_id in customer_ids:
        # Home address for every customer
        addresses.append({
            "customer_id": customer_id,
            "address_type": "home",
            "street_line1": fake.street_address(),
            "street_line2": None if fake.boolean(chance_of_getting_true=70) else fake.secondary_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "postal_code": fake.zipcode(),
            "country": "USA",
            "is_verified": fake.boolean(chance_of_getting_true=80)
        })
        
        # Work address for some customers (50% chance)
        if fake.boolean(chance_of_getting_true=50):
            addresses.append({
                "customer_id": customer_id,
                "address_type": "work",
                "street_line1": fake.street_address(),
                "street_line2": fake.secondary_address() if fake.boolean(chance_of_getting_true=60) else None,
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postal_code": fake.zipcode(),
                "country": "USA",
                "is_verified": fake.boolean(chance_of_getting_true=80)
            })
    
    # Insert addresses
    cursor = conn.cursor()
    for address in addresses:
        cursor.execute(
            """
            INSERT INTO addresses 
            (customer_id, address_type, street_line1, street_line2, city, state, postal_code, country, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                address["customer_id"], address["address_type"], address["street_line1"], 
                address["street_line2"], address["city"], address["state"], 
                address["postal_code"], address["country"], address["is_verified"]
            )
        )
    
    # Get address IDs with their associated customer IDs
    cursor.execute("SELECT address_id, customer_id FROM addresses")
    address_data = [(row[0], row[1]) for row in cursor.fetchall()]
    
    return address_data


def generate_and_insert_materials(conn: sqlite3.Connection) -> List[int]:
    """
    Generate and insert material data.
    
    Args:
        conn: Database connection
        
    Returns:
        List of generated material IDs
    """
    materials = [
        {
            "name": "Standard Envelope", 
            "description": "Standard #10 business envelope", 
            "unit_cost": round(random.uniform(0.04, 0.06), 2), 
            "unit_type": "each"
        },
        {
            "name": "Large Envelope", 
            "description": "9x12 manila envelope", 
            "unit_cost": round(random.uniform(0.14, 0.16), 2), 
            "unit_type": "each"
        },
        {
            "name": "Standard Paper", 
            "description": "20lb 8.5x11 white paper", 
            "unit_cost": round(random.uniform(0.01, 0.03), 2), 
            "unit_type": "sheet"
        },
        {
            "name": "Premium Paper", 
            "description": "24lb 8.5x11 ivory paper", 
            "unit_cost": round(random.uniform(0.03, 0.05), 2), 
            "unit_type": "sheet"
        },
        {
            "name": "Ink - Black", 
            "description": "Black printer ink", 
            "unit_cost": round(random.uniform(0.08, 0.12), 2), 
            "unit_type": "page"
        }
    ]
    
    # Insert materials
    cursor = conn.cursor()
    for material in materials:
        cursor.execute(
            "INSERT INTO materials (name, description, unit_cost, unit_type) VALUES (?, ?, ?, ?)",
            (material["name"], material["description"], material["unit_cost"], material["unit_type"])
        )
    
    # Get material IDs
    cursor.execute("SELECT material_id FROM materials")
    material_ids = [row[0] for row in cursor.fetchall()]
    
    return material_ids


def generate_and_insert_inventory(conn: sqlite3.Connection, material_ids: List[int]) -> List[Dict]:
    """
    Generate and insert inventory data.
    
    Args:
        conn: Database connection
        material_ids: List of material IDs to create inventory for
        
    Returns:
        List of inventory entries
    """
    inventory = []
    warehouses = ["Warehouse A", "Warehouse B", "Warehouse C"]
    
    for i, material_id in enumerate(material_ids):
        inventory.append({
            "material_id": material_id,
            "quantity": random.randint(500, 5000),
            "location": random.choice(warehouses),
            "last_restock_date": fake.date_between(start_date="-30d", end_date="today").strftime("%Y-%m-%d")
        })
    
    # Insert inventory
    cursor = conn.cursor()
    for inv in inventory:
        cursor.execute(
            "INSERT INTO inventory (material_id, quantity, location, last_restock_date) VALUES (?, ?, ?, ?)",
            (inv["material_id"], inv["quantity"], inv["location"], inv["last_restock_date"])
        )
    
    return inventory


def generate_and_insert_mailing_lists(conn: sqlite3.Connection) -> List[int]:
    """
    Generate and insert mailing list data.
    
    Args:
        conn: Database connection
        
    Returns:
        List of generated list IDs
    """
    list_types = ["Newsletter", "Promotion", "Announcement", "Update", "Special Offer"]
    departments = ["Marketing", "Sales", "Product", "Support", "Admin"]
    
    mailing_lists = []
    for i in range(3):  # Create 3 mailing lists
        list_type = random.choice(list_types)
        department = random.choice(departments)
        mailing_lists.append({
            "name": f"{department} {list_type}",
            "description": f"{department} department's {list_type.lower()} mailing list",
            "created_by": department.lower()
        })
    
    # Insert mailing lists
    cursor = conn.cursor()
    for ml in mailing_lists:
        cursor.execute(
            "INSERT INTO mailing_lists (name, description, created_by) VALUES (?, ?, ?)",
            (ml["name"], ml["description"], ml["created_by"])
        )
    
    # Get list IDs
    cursor.execute("SELECT list_id FROM mailing_lists")
    list_ids = [row[0] for row in cursor.fetchall()]
    
    return list_ids


def generate_and_insert_list_members(
    conn: sqlite3.Connection, 
    list_ids: List[int], 
    customer_ids: List[int],
    address_data: List[Tuple[int, int]]
) -> List[Dict]:
    """
    Generate and insert list member data.
    
    Args:
        conn: Database connection
        list_ids: List of mailing list IDs
        customer_ids: List of customer IDs
        address_data: List of (address_id, customer_id) tuples
        
    Returns:
        List of list member entries
    """
    list_members = []
    
    # Create a mapping of customer_id to address_ids for easier lookup
    customer_to_addresses = {}
    for address_id, customer_id in address_data:
        if customer_id not in customer_to_addresses:
            customer_to_addresses[customer_id] = []
        customer_to_addresses[customer_id].append(address_id)
    
    for list_id in list_ids:
        # Randomly select some customers for each list (50-80% of customers)
        selected_customers = random.sample(
            customer_ids, 
            k=random.randint(len(customer_ids) // 2, int(len(customer_ids) * 0.8))
        )
        
        for customer_id in selected_customers:
            # Choose a random address for this customer
            if customer_id in customer_to_addresses and customer_to_addresses[customer_id]:
                address_id = random.choice(customer_to_addresses[customer_id])
                
                list_members.append({
                    "list_id": list_id,
                    "customer_id": customer_id,
                    "address_id": address_id,
                    "status": random.choice(["active", "inactive", "pending"]) if fake.boolean(chance_of_getting_true=20) else "active"
                })
    
    # Insert list members
    cursor = conn.cursor()
    for member in list_members:
        cursor.execute(
            "INSERT INTO list_members (list_id, customer_id, address_id, status) VALUES (?, ?, ?, ?)",
            (member["list_id"], member["customer_id"], member["address_id"], member["status"])
        )
    
    return list_members


def generate_and_insert_campaigns(conn: sqlite3.Connection, list_ids: List[int]) -> List[int]:
    """
    Generate and insert campaign data.
    
    Args:
        conn: Database connection
        list_ids: List of mailing list IDs
        
    Returns:
        List of generated campaign IDs
    """
    campaign_types = ["Newsletter", "Promotion", "Announcement", "Holiday", "Special Offer"]
    campaign_statuses = ["draft", "active", "paused", "completed"]
    
    campaigns = []
    for i in range(min(len(list_ids) * 2, 5)):  # Create up to 5 campaigns
        # Generate random dates
        start_date = fake.date_between(start_date="-10d", end_date="+20d")
        end_date = fake.date_between(start_date=start_date, end_date=start_date + timedelta(days=30))
        
        campaign_type = random.choice(campaign_types)
        list_id = random.choice(list_ids)
        
        campaigns.append({
            "name": f"{fake.month_name()} {campaign_type}",
            "description": f"{campaign_type} for {fake.month_name()}",
            "list_id": list_id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "status": random.choice(campaign_statuses)
        })
    
    # Insert campaigns
    cursor = conn.cursor()
    for campaign in campaigns:
        cursor.execute(
            """
            INSERT INTO mailing_campaigns 
            (name, description, list_id, start_date, end_date, status) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                campaign["name"], campaign["description"], campaign["list_id"],
                campaign["start_date"], campaign["end_date"], campaign["status"]
            )
        )
    
    # Get campaign IDs
    cursor.execute("SELECT campaign_id FROM mailing_campaigns")
    campaign_ids = [row[0] for row in cursor.fetchall()]
    
    return campaign_ids


def generate_and_insert_mail_items(
    conn: sqlite3.Connection, 
    campaign_ids: List[int], 
    list_members: List[Dict]
) -> List[int]:
    """
    Generate and insert mail item data.
    
    Args:
        conn: Database connection
        campaign_ids: List of campaign IDs
        list_members: List of list member entries
        
    Returns:
        List of generated mail item IDs
    """
    mail_items = []
    
    # Group list members by list_id for easier lookup
    members_by_list = {}
    for member in list_members:
        list_id = member["list_id"]
        if list_id not in members_by_list:
            members_by_list[list_id] = []
        members_by_list[list_id].append(member)
    
    # Get campaign details
    cursor = conn.cursor()
    cursor.execute("SELECT campaign_id, list_id FROM mailing_campaigns")
    campaign_to_list = {row[0]: row[1] for row in cursor.fetchall()}
    
    for campaign_id in campaign_ids:
        list_id = campaign_to_list.get(campaign_id)
        if list_id and list_id in members_by_list:
            # Create mail items for members of this list
            for member in members_by_list[list_id]:
                if member["status"] == "active":  # Only create mail items for active members
                    mail_items.append({
                        "campaign_id": campaign_id,
                        "customer_id": member["customer_id"],
                        "address_id": member["address_id"],
                        "content_template": f"template_{campaign_id}",
                        "status": random.choice(["pending", "processed", "cancelled"]) if fake.boolean(chance_of_getting_true=20) else "pending"
                    })
    
    # Insert mail items
    for item in mail_items:
        cursor.execute(
            """
            INSERT INTO mail_items 
            (campaign_id, customer_id, address_id, content_template, status) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item["campaign_id"], item["customer_id"], item["address_id"],
                item["content_template"], item["status"]
            )
        )
    
    # Get mail item IDs
    cursor.execute("SELECT item_id FROM mail_items")
    mail_item_ids = [row[0] for row in cursor.fetchall()]
    
    return mail_item_ids


def generate_and_insert_print_jobs(conn: sqlite3.Connection) -> List[int]:
    """
    Generate and insert print job data.
    
    Args:
        conn: Database connection
        
    Returns:
        List of generated print job IDs
    """
    print_jobs = []
    
    # Create 2-3 print jobs
    for i in range(random.randint(2, 3)):
        scheduled_date = fake.date_between(start_date="-5d", end_date="+10d")
        
        print_jobs.append({
            "name": f"Batch {fake.random_int(min=100, max=999)}",
            "description": f"Print job for {scheduled_date.strftime('%B %d')}",
            "status": random.choice(["queued", "processing", "completed"]),
            "scheduled_date": scheduled_date.strftime("%Y-%m-%d")
        })
    
    # Insert print jobs
    cursor = conn.cursor()
    for job in print_jobs:
        cursor.execute(
            """
            INSERT INTO print_jobs 
            (name, description, status, scheduled_date) 
            VALUES (?, ?, ?, ?)
            """,
            (job["name"], job["description"], job["status"], job["scheduled_date"])
        )
    
    # Get print job IDs
    cursor.execute("SELECT job_id FROM print_jobs")
    job_ids = [row[0] for row in cursor.fetchall()]
    
    return job_ids


def generate_and_insert_print_queue(
    conn: sqlite3.Connection, 
    job_ids: List[int], 
    mail_item_ids: List[int]
) -> List[Dict]:
    """
    Generate and insert print queue data.
    
    Args:
        conn: Database connection
        job_ids: List of print job IDs
        mail_item_ids: List of mail item IDs
        
    Returns:
        List of print queue entries
    """
    print_queue = []
    
    # Distribute mail items across print jobs
    items_per_job = len(mail_item_ids) // len(job_ids) if job_ids else 0
    
    if items_per_job > 0:
        for i, job_id in enumerate(job_ids):
            # Get a slice of mail items for this job
            start_idx = i * items_per_job
            end_idx = start_idx + items_per_job if i < len(job_ids) - 1 else len(mail_item_ids)
            job_items = mail_item_ids[start_idx:end_idx]
            
            for order, item_id in enumerate(job_items, 1):
                print_queue.append({
                    "job_id": job_id,
                    "item_id": item_id,
                    "print_order": order,
                    "status": random.choice(["queued", "processing", "completed"]),
                    "printed_at": fake.date_time_this_month().strftime("%Y-%m-%d") if fake.boolean(chance_of_getting_true=70) else None
                })
    
    # Insert print queue entries
    cursor = conn.cursor()
    for entry in print_queue:
        if entry["printed_at"]:
            cursor.execute(
                """
                INSERT INTO print_queue 
                (job_id, item_id, print_order, status, printed_at) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (entry["job_id"], entry["item_id"], entry["print_order"], entry["status"], entry["printed_at"])
            )
        else:
            cursor.execute(
                """
                INSERT INTO print_queue 
                (job_id, item_id, print_order, status) 
                VALUES (?, ?, ?, ?)
                """,
                (entry["job_id"], entry["item_id"], entry["print_order"], entry["status"])
            )
    
    return print_queue


def generate_and_insert_delivery_tracking(
    conn: sqlite3.Connection, 
    mail_item_ids: List[int]
) -> List[Dict]:
    """
    Generate and insert delivery tracking data.
    
    Args:
        conn: Database connection
        mail_item_ids: List of mail item IDs
        
    Returns:
        List of delivery tracking entries
    """
    tracking_entries = []
    carriers = ["USPS", "UPS", "FedEx"]
    statuses = ["pending", "shipped", "delivered", "returned"]
    
    # Create tracking entries for some mail items (60-80%)
    num_items = random.randint(int(len(mail_item_ids) * 0.6), int(len(mail_item_ids) * 0.8))
    selected_items = random.sample(mail_item_ids, k=min(num_items, len(mail_item_ids)))
    
    for item_id in selected_items:
        shipped_date = fake.date_time_this_month().strftime("%Y-%m-%d")
        carrier = random.choice(carriers)
        
        # Calculate delivery dates based on shipped date
        delivery_date = fake.date_time_between(
            start_date=datetime.strptime(shipped_date, "%Y-%m-%d"), 
            end_date="+5d"
        ).strftime("%Y-%m-%d") if fake.boolean(chance_of_getting_true=60) else None
        
        # Estimated delivery is always set, actual delivery only if delivered
        estimated_date = fake.date_time_between(
            start_date=datetime.strptime(shipped_date, "%Y-%m-%d"), 
            end_date="+3d"
        ).strftime("%Y-%m-%d")
        
        tracking_entries.append({
            "item_id": item_id,
            "tracking_number": fake.uuid4().replace("-", "")[:16].upper(),
            "carrier": carrier,
            "status": random.choice(statuses),
            "shipped_date": shipped_date,
            "estimated_delivery": estimated_date,
            "actual_delivery": delivery_date
        })
    
    # Insert tracking entries
    cursor = conn.cursor()
    for entry in tracking_entries:
        if entry["actual_delivery"]:
            cursor.execute(
                """
                INSERT INTO delivery_tracking 
                (item_id, tracking_number, carrier, status, shipped_date, estimated_delivery, actual_delivery) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["item_id"], entry["tracking_number"], entry["carrier"],
                    entry["status"], entry["shipped_date"], entry["estimated_delivery"], entry["actual_delivery"]
                )
            )
        else:
            cursor.execute(
                """
                INSERT INTO delivery_tracking 
                (item_id, tracking_number, carrier, status, shipped_date, estimated_delivery) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["item_id"], entry["tracking_number"], entry["carrier"],
                    entry["status"], entry["shipped_date"], entry["estimated_delivery"]
                )
            )
    
    return tracking_entries


if __name__ == "__main__":
    # If run directly, generate sample data
    db_path = Path(__file__).parent.parent / "data" / "mail.db"
    generate_sample_data(db_path)
