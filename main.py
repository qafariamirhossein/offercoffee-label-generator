#!/usr/bin/env python3
"""
Main script for WooCommerce Label Generation
اسکریپت اصلی برای تولید لیبل از داده‌های ووکامرس
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# Import our modules
from woocommerce_api import WooCommerceAPI, format_order_data
from label_generator import LabelGenerator
from config import Config

class WooCommerceLabelManager:
    """Main class for managing WooCommerce label generation"""
    
    def __init__(self):
        """Initialize the label manager"""
        self.config = Config()
        self.api = None
        self.label_generator = None
        self.setup()
    
    def setup(self):
        """Setup API connection and label generator"""
        # Validate configuration
        if not self.config.validate_config():
            print("❌ لطفاً تنظیمات ووکامرس را در فایل config.py یا متغیرهای محیطی تنظیم کنید")
            sys.exit(1)
        
        # Create necessary directories
        self.config.create_directories()
        
        # Initialize WooCommerce API
        woo_config = self.config.get_woocommerce_config()
        self.api = WooCommerceAPI(
            store_url=woo_config['store_url'],
            consumer_key=woo_config['consumer_key'],
            consumer_secret=woo_config['consumer_secret']
        )
        
        # Initialize label generator
        label_config = self.config.get_label_config()
        self.label_generator = LabelGenerator(
            font_en_path=label_config['font_en'],
            font_fa_path=label_config['font_fa']
        )
        
        print("✅ سیستم آماده است")
    
    def test_connection(self) -> bool:
        """Test WooCommerce API connection"""
        print("🔍 در حال تست اتصال به ووکامرس...")
        if self.api.test_connection():
            print("✅ اتصال به ووکامرس موفق بود")
            return True
        else:
            print("❌ خطا در اتصال به ووکامرس")
            return False
    
    def get_orders(self, status: str = 'processing', limit: int = 10) -> List[Dict]:
        """Get orders from WooCommerce"""
        print(f"📦 در حال دریافت سفارشات با وضعیت '{status}'...")
        orders = self.api.get_orders(status=status, per_page=limit)
        
        if orders:
            print(f"✅ {len(orders)} سفارش دریافت شد")
            return orders
        else:
            print("❌ هیچ سفارشی یافت نشد")
            return []
    
    def generate_labels_for_orders(self, orders: List[Dict], label_type: str = 'basic') -> List[str]:
        """
        Generate labels for a list of orders
        
        Args:
            orders: List of order data from WooCommerce
            label_type: Type of label ('basic', 'product', 'customer')
            
        Returns:
            List of generated label file paths
        """
        generated_files = []
        output_dir = self.config.PATHS['output']
        
        print(f"🏷️  در حال تولید {len(orders)} لیبل از نوع '{label_type}'...")
        
        for i, order in enumerate(orders):
            try:
                # Format order data
                formatted_order = format_order_data(order)
                order_id = formatted_order['order_id']
                order_number = formatted_order['order_number']
                
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"label_{order_number}_{timestamp}_{label_type}.png"
                filepath = os.path.join(output_dir, filename)
                
                # Generate label based on type
                if label_type == 'basic':
                    self.label_generator.generate_basic_label(formatted_order, filepath)
                elif label_type == 'product':
                    # Extract product info from first product
                    product_info = None
                    if formatted_order['products']:
                        first_product = formatted_order['products'][0]
                        product_info = {
                            'composition': 'روبوستا اندونزی',  # Default or from product meta
                            'weight': '1000',  # Default or from product meta
                            'grind': 'خیر'  # Default or from product meta
                        }
                    self.label_generator.generate_product_label(formatted_order, product_info, filepath)
                elif label_type == 'customer':
                    self.label_generator.generate_customer_label(formatted_order, filepath)
                else:
                    print(f"❌ نوع لیبل نامعتبر: {label_type}")
                    continue
                
                generated_files.append(filepath)
                print(f"✅ لیبل سفارش {order_number} تولید شد")
                
            except Exception as e:
                print(f"❌ خطا در تولید لیبل سفارش {order.get('id', 'نامشخص')}: {e}")
                continue
        
        print(f"🎉 {len(generated_files)} لیبل با موفقیت تولید شد")
        return generated_files
    
    def process_orders(self, status: str = 'processing', limit: int = 10, 
                      label_type: str = 'basic', update_status: bool = False) -> List[str]:
        """
        Complete workflow: get orders, generate labels, optionally update status
        
        Args:
            status: Order status to process
            limit: Maximum number of orders to process
            label_type: Type of labels to generate
            update_status: Whether to update order status after label generation
            
        Returns:
            List of generated label file paths
        """
        # Test connection first
        if not self.test_connection():
            return []
        
        # Get orders
        orders = self.get_orders(status=status, limit=limit)
        if not orders:
            return []
        
        # Generate labels
        generated_files = self.generate_labels_for_orders(orders, label_type)
        
        # Update order status if requested
        if update_status and generated_files:
            new_status = self.config.ORDERS['status_after_label']
            print(f"🔄 در حال تغییر وضعیت سفارشات به '{new_status}'...")
            
            for order in orders:
                order_id = order['id']
                if self.api.update_order_status(order_id, new_status):
                    print(f"✅ وضعیت سفارش {order_id} به {new_status} تغییر یافت")
                else:
                    print(f"❌ خطا در تغییر وضعیت سفارش {order_id}")
        
        return generated_files
    
    def generate_single_label(self, order_id: int, label_type: str = 'basic') -> Optional[str]:
        """
        Generate label for a single order by ID
        
        Args:
            order_id: WooCommerce order ID
            label_type: Type of label to generate
            
        Returns:
            Generated label file path or None
        """
        print(f"🔍 در حال دریافت سفارش {order_id}...")
        order = self.api.get_order_by_id(order_id)
        
        if not order:
            print(f"❌ سفارش {order_id} یافت نشد")
            return None
        
        # Format order data
        formatted_order = format_order_data(order)
        
        # Generate label
        generated_files = self.generate_labels_for_orders([order], label_type)
        return generated_files[0] if generated_files else None

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='WooCommerce Label Generator')
    parser.add_argument('--test', action='store_true', help='Test WooCommerce connection')
    parser.add_argument('--orders', type=str, default='processing', 
                       help='Order status to process (default: processing)')
    parser.add_argument('--limit', type=int, default=10, 
                       help='Maximum number of orders to process (default: 10)')
    parser.add_argument('--type', type=str, choices=['basic', 'product', 'customer'], 
                       default='basic', help='Label type to generate (default: basic)')
    parser.add_argument('--order-id', type=int, help='Generate label for specific order ID')
    parser.add_argument('--update-status', action='store_true', 
                       help='Update order status after label generation')
    parser.add_argument('--list-orders', action='store_true', 
                       help='List recent orders without generating labels')
    
    args = parser.parse_args()
    
    # Initialize label manager
    manager = WooCommerceLabelManager()
    
    if args.test:
        # Test connection only
        manager.test_connection()
    
    elif args.list_orders:
        # List orders without generating labels
        if manager.test_connection():
            orders = manager.get_orders(status=args.orders, limit=args.limit)
            if orders:
                print("\n📋 لیست سفارشات:")
                for order in orders:
                    print(f"  سفارش {order['number']}: {order['status']} - {order['total']} {order['currency']}")
    
    elif args.order_id:
        # Generate label for specific order
        manager.generate_single_label(args.order_id, args.type)
    
    else:
        # Process orders and generate labels
        manager.process_orders(
            status=args.orders,
            limit=args.limit,
            label_type=args.type,
            update_status=args.update_status
        )

if __name__ == "__main__":
    main()
