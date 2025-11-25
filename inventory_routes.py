from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from db import db

inventory_bp = Blueprint("inventory", __name__)
inventory_collection = db["electronics_inventory"]

# Helper to convert ObjectId to string
def serialize_item(item):
    item["_id"] = str(item["_id"])
    return item


# Helper to validate required fields
def validate_electronics_data(data, is_update=False):
    required_fields = ["name", "category", "stock", "min_stock", "supplier"]
    
    if not is_update:
        # For new items, all fields are required
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Validate data types
    if "stock" in data:
        try:
            stock = int(data["stock"])
            if stock < 0:
                return False, "Stock quantity must be non-negative"
        except (ValueError, TypeError):
            return False, "Stock must be a valid number"
    
    if "min_stock" in data:
        try:
            min_stock = int(data["min_stock"])
            if min_stock < 0:
                return False, "Minimum stock must be non-negative"
        except (ValueError, TypeError):
            return False, "Minimum stock must be a valid number"
    
    # Validate category
    valid_categories = [
        "Microcontroller", "Sensor", "Motor", "Display", 
        "Power Supply", "Communication Module", "Storage", 
        "Passive Component", "Other"
    ]
    if "category" in data and data["category"] not in valid_categories:
        return False, f"Invalid category. Must be one of: {', '.join(valid_categories)}"
    
    return True, None


# Helper to determine stock status
def get_stock_status(stock, min_stock):
    if stock <= min_stock:
        return "Low Stock"
    return "In Stock"


# ✅ Add electronics component
@inventory_bp.route("/add-electronics", methods=["POST"])
def add_electronics():
    try:
        data = request.json
        
        # Validate data
        is_valid, error_message = validate_electronics_data(data)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Prepare new item
        stock = int(data["stock"])
        min_stock = int(data["min_stock"])
        
        new_item = {
            "name": data["name"],
            "category": data["category"],
            "stock": stock,
            "min_stock": min_stock,
            "specifications": data.get("specifications", ""),
            "supplier": data["supplier"],
            "status": get_stock_status(stock, min_stock),
            "date_added": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Insert into database
        result = inventory_collection.insert_one(new_item)
        new_item["_id"] = str(result.inserted_id)
        
        return jsonify({
            "message": "Electronics component added successfully",
            "electronics": new_item
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to add component: {str(e)}"}), 500


# ✅ Fetch all electronics items
@inventory_bp.route("/all-items", methods=["GET"])
def get_all_electronics():
    try:
        items = list(inventory_collection.find())
        items = [serialize_item(item) for item in items]
        
        return jsonify({
            "count": len(items),
            "electronics": items
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch electronics: {str(e)}"}), 500


# ✅ Get single electronics item by ID - FIXED ROUTE
@inventory_bp.route("/items/<item_id>", methods=["GET"])
def get_electronics_by_id(item_id):
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(item_id):
            return jsonify({"error": "Invalid item ID"}), 400
        
        item = inventory_collection.find_one({"_id": ObjectId(item_id)})
        
        if not item:
            return jsonify({"error": "Component not found"}), 404
        
        return jsonify(serialize_item(item)), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch component: {str(e)}"}), 500


# ✅ Update electronics component - FIXED ROUTE
@inventory_bp.route("/items/<item_id>", methods=["PUT"])
def update_electronics(item_id):
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(item_id):
            return jsonify({"error": "Invalid item ID"}), 400
        
        data = request.json
        
        # Validate data
        is_valid, error_message = validate_electronics_data(data, is_update=True)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Prepare update data
        update_data = {
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Add fields that are present in request
        if "name" in data:
            update_data["name"] = data["name"]
        if "category" in data:
            update_data["category"] = data["category"]
        if "stock" in data:
            update_data["stock"] = int(data["stock"])
        if "min_stock" in data:
            update_data["min_stock"] = int(data["min_stock"])
        if "specifications" in data:
            update_data["specifications"] = data["specifications"]
        if "supplier" in data:
            update_data["supplier"] = data["supplier"]
        
        # Update status based on stock levels
        if "stock" in update_data or "min_stock" in update_data:
            # Get current values if not in update
            current_item = inventory_collection.find_one({"_id": ObjectId(item_id)})
            if not current_item:
                return jsonify({"error": "Component not found"}), 404
            
            stock = update_data.get("stock", current_item["stock"])
            min_stock = update_data.get("min_stock", current_item["min_stock"])
            update_data["status"] = get_stock_status(stock, min_stock)
        
        # Update in database
        result = inventory_collection.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Component not found"}), 404
        
        # Fetch and return updated item
        updated_item = inventory_collection.find_one({"_id": ObjectId(item_id)})
        
        return jsonify({
            "message": "Component updated successfully",
            "electronics": serialize_item(updated_item)
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update component: {str(e)}"}), 500


# ✅ Delete electronics component - FIXED ROUTE
@inventory_bp.route("/items/<item_id>", methods=["DELETE"])
def delete_electronics(item_id):
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(item_id):
            return jsonify({"error": "Invalid item ID"}), 400
        
        result = inventory_collection.delete_one({"_id": ObjectId(item_id)})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Component not found"}), 404
        
        return jsonify({
            "message": "Component deleted successfully",
            "deleted_id": item_id
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to delete component: {str(e)}"}), 500


# ✅ Get low stock items
@inventory_bp.route("/low-stock", methods=["GET"])
def get_low_stock_items():
    try:
        # Find items where stock <= min_stock
        items = list(inventory_collection.find({
            "$expr": {"$lte": ["$stock", "$min_stock"]}
        }))
        
        items = [serialize_item(item) for item in items]
        
        return jsonify({
            "count": len(items),
            "low_stock_items": items
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch low stock items: {str(e)}"}), 500


# ✅ Get items by category
@inventory_bp.route("/category/<category>", methods=["GET"])
def get_by_category(category):
    try:
        items = list(inventory_collection.find({"category": category}))
        items = [serialize_item(item) for item in items]
        
        return jsonify({
            "category": category,
            "count": len(items),
            "items": items
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch items by category: {str(e)}"}), 500


# ✅ Search electronics components
@inventory_bp.route("/search", methods=["GET"])
def search_electronics():
    try:
        query = request.args.get("q", "")
        
        if not query:
            return jsonify({"error": "Search query is required"}), 400
        
        # Search in name, category, specifications, and supplier
        items = list(inventory_collection.find({
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"category": {"$regex": query, "$options": "i"}},
                {"specifications": {"$regex": query, "$options": "i"}},
                {"supplier": {"$regex": query, "$options": "i"}}
            ]
        }))
        
        items = [serialize_item(item) for item in items]
        
        return jsonify({
            "query": query,
            "count": len(items),
            "results": items
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


# ✅ Get inventory statistics
@inventory_bp.route("/stats", methods=["GET"])
def get_statistics():
    try:
        total_components = inventory_collection.count_documents({})
        
        low_stock = inventory_collection.count_documents({
            "$expr": {"$lte": ["$stock", "$min_stock"]}
        })
        
        # Total stock quantity
        pipeline = [
            {"$group": {"_id": None, "total_stock": {"$sum": "$stock"}}}
        ]
        result = list(inventory_collection.aggregate(pipeline))
        total_stock = result[0]["total_stock"] if result else 0
        
        # Count by category
        category_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        categories = list(inventory_collection.aggregate(category_pipeline))
        
        return jsonify({
            "total_components": total_components,
            "low_stock_items": low_stock,
            "total_stock": total_stock,
            "categories": {cat["_id"]: cat["count"] for cat in categories}
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch statistics: {str(e)}"}), 500


# 📌 REPORTS & ANALYTICS ENDPOINTS
@inventory_bp.route("/reports/stock-summary", methods=["GET"])
def stock_summary():
    try:
        total_items = inventory_collection.count_documents({})
        
        low_stock_items = inventory_collection.count_documents({
            "$expr": {"$lte": ["$stock", "$min_stock"]}
        })
        
        in_stock_items = total_items - low_stock_items
        
        # Total stock quantity
        pipeline_total = [
            {"$group": {"_id": None, "total_stock": {"$sum": "$stock"}}}
        ]
        result = list(inventory_collection.aggregate(pipeline_total))
        total_stock = result[0]["total_stock"] if result else 0

        return jsonify({
            "total_items": total_items,
            "low_stock_items": low_stock_items,
            "in_stock_items": in_stock_items,
            "total_stock_quantity": total_stock
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to generate stock summary: {str(e)}"}), 500


@inventory_bp.route("/reports/category-breakdown", methods=["GET"])
def category_breakdown():
    try:
        pipeline = [
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1},
                "total_stock": {"$sum": "$stock"}
            }}
        ]

        result = list(inventory_collection.aggregate(pipeline))

        return jsonify({
            "categories": [
                {
                    "category": item["_id"],
                    "count": item["count"],
                    "total_stock": item["total_stock"]
                } for item in result
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get category breakdown: {str(e)}"}), 500


@inventory_bp.route("/reports/supplier-performance", methods=["GET"])
def supplier_performance():
    try:
        pipeline = [
            {"$group": {
                "_id": "$supplier",
                "total_items": {"$sum": 1},
                "total_stock": {"$sum": "$stock"},
                "low_stock": {
                    "$sum": {
                        "$cond": [
                            {"$lte": ["$stock", "$min_stock"]}, 1, 0
                        ]
                    }
                }
            }}
        ]

        suppliers = list(inventory_collection.aggregate(pipeline))

        return jsonify({
            "suppliers": [
                {
                    "supplier": item["_id"],
                    "total_items": item["total_items"],
                    "total_stock": item["total_stock"],
                    "low_stock_items": item["low_stock"]
                }
                for item in suppliers
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to generate supplier report: {str(e)}"}), 500


@inventory_bp.route("/reports/usage-trends", methods=["GET"])
def usage_trends():
    try:
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "year": {"$year": {"$toDate": "$date_added"}},
                        "month": {"$month": {"$toDate": "$date_added"}}
                    },
                    "items_added": {"$sum": 1}
                }
            },
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]

        trend_data = list(inventory_collection.aggregate(pipeline))

        return jsonify({
            "monthly_trends": [
                {
                    "year": item["_id"]["year"],
                    "month": item["_id"]["month"],
                    "items_added": item["items_added"]
                }
                for item in trend_data
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get usage trends: {str(e)}"}), 500


# 📌 FULL REPORT (dashboard style)
@inventory_bp.route("/reports/full-report", methods=["GET"])
def full_report():
    try:
        # Reuse other pipelines
        total_items = inventory_collection.count_documents({})
        low_stock = inventory_collection.count_documents({"$expr": {"$lte": ["$stock", "$min_stock"]}})

        category_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}, "total_stock": {"$sum": "$stock"}}}
        ]
        categories = list(inventory_collection.aggregate(category_pipeline))

        supplier_pipeline = [
            {"$group": {
                "_id": "$supplier",
                "count": {"$sum": 1},
                "low_stock": {"$sum": {"$cond": [{"$lte": ["$stock", "$min_stock"]}, 1, 0]}}
            }}
        ]
        suppliers = list(inventory_collection.aggregate(supplier_pipeline))

        return jsonify({
            "overview": {
                "total_items": total_items,
                "low_stock": low_stock
            },
            "categories": categories,
            "suppliers": suppliers
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to generate full report: {str(e)}"}), 500