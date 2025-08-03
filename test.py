import pyodbc

def test_database_access():
    """Test basic database access with simple queries"""
    
    connection_string = "Driver={ODBC Driver 18 for SQL Server};Server=tcp:shamal-server.database.windows.net,1433;Database=Shamal-uae-db;Uid=uae-server;Pwd=Shamal-work;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    
    try:
        print("Connecting to database...")
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        print("✅ Connection successful!")
        
        # Test 1: Basic server info
        print("\n--- Test 1: Server Information ---")
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"SQL Server Version: {version[:80]}...")
        
        # Test 2: Current database
        print("\n--- Test 2: Database Information ---")
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"Current Database: {db_name}")
        
        # Test 3: Current user
        print("\n--- Test 3: User Information ---")
        cursor.execute("SELECT SYSTEM_USER, USER_NAME()")
        user_info = cursor.fetchone()
        print(f"System User: {user_info[0]}")
        print(f"Database User: {user_info[1]}")
        
        # Test 4: List all tables
        print("\n--- Test 4: Tables in Database ---")
        cursor.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"Found {len(tables)} tables/views:")
            for table in tables:
                print(f"  {table[0]}.{table[1]} ({table[2]})")
        else:
            print("No tables found in database")
        
        # Test 5: Database size and info
        print("\n--- Test 5: Database Statistics ---")
        cursor.execute("""
            SELECT 
                name as database_name,
                database_id,
                create_date,
                collation_name
            FROM sys.databases 
            WHERE name = DB_NAME()
        """)
        db_info = cursor.fetchone()
        if db_info:
            print(f"Database ID: {db_info[1]}")
            print(f"Created: {db_info[2]}")
            print(f"Collation: {db_info[3]}")
        
        # Test 6: Check permissions
        print("\n--- Test 6: User Permissions ---")
        cursor.execute("""
            SELECT 
                permission_name,
                state_desc
            FROM sys.database_permissions dp
            JOIN sys.database_principals pr ON dp.grantee_principal_id = pr.principal_id
            WHERE pr.name = USER_NAME()
        """)
        permissions = cursor.fetchall()
        
        if permissions:
            print("User permissions:")
            for perm in permissions:
                print(f"  {perm[0]}: {perm[1]}")
        else:
            print("No specific permissions found (may have default access)")
        
        cursor.close()
        conn.close()
        print("\n✅ All tests completed successfully!")
        return True
        
    except pyodbc.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Database Access")
    print("=" * 40)
    test_database_access()