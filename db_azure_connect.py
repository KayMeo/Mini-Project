# db_azure_connect.py
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# 1. Cấu hình kết nối (Dùng thông tin bạn cung cấp)
# Lưu ý: "TrustServerCertificate=yes" thường cần thiết khi kết nối IP trực tiếp để tránh lỗi SSL
SERVER = '34.87.137.36'
DATABASE = 'AdventureWorksDW2019'
USERNAME = 'SA'
PASSWORD = 'huydata_2025'
DRIVER = 'ODBC Driver 17 for SQL Server'

connection_string = f"mssql+pyodbc://{USERNAME}:{PASSWORD}@{SERVER}/{DATABASE}?driver={DRIVER}&TrustServerCertificate=yes"

engine = create_engine(connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Mapping các bảng AdventureWorks

class DimProductCategory(Base):
    __tablename__ = 'DimProductCategory'
    ProductCategoryKey = Column(Integer, primary_key=True)
    EnglishProductCategoryName = Column(String)
    # Quan hệ ngược
    subcategories = relationship("DimProductSubcategory", back_populates="category")

class DimProductSubcategory(Base):
    __tablename__ = 'DimProductSubcategory'
    ProductSubcategoryKey = Column(Integer, primary_key=True)
    EnglishProductSubcategoryName = Column(String)
    ProductCategoryKey = Column(Integer, ForeignKey('DimProductCategory.ProductCategoryKey'))
    # Quan hệ
    category = relationship("DimProductCategory", back_populates="subcategories")
    products = relationship("DimProduct", back_populates="subcategory")

class DimProduct(Base):
    __tablename__ = 'DimProduct'
    ProductKey = Column(Integer, primary_key=True)
    EnglishProductName = Column(String)
    ProductSubcategoryKey = Column(Integer, ForeignKey('DimProductSubcategory.ProductSubcategoryKey'))
    EnglishDescription = Column(String)
    ListPrice = Column(Float)
    # Giả lập tồn kho vì bảng Dim thường không có Stock động (trong thực tế sẽ join với FactInventory)
    # Ở đây ta map tạm để lấy thông tin tĩnh
    SafetyStockLevel = Column(Integer) # Mức an toàn (Max)
    ReorderPoint = Column(Integer)     # Điểm đặt hàng lại (Min)
    subcategory = relationship("DimProductSubcategory", back_populates="products")

class FactInternetSales(Base):
    __tablename__ = 'FactInternetSales'
    SalesOrderNumber = Column(String, primary_key=True) # Composite key thực tế phức tạp hơn, đây demo
    SalesOrderLineNumber = Column(Integer, primary_key=True)
    ProductKey = Column(Integer, ForeignKey('DimProduct.ProductKey'))
    OrderQuantity = Column(Integer)
    UnitPrice = Column(Float)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- PHẦN KIỂM TRA KẾT NỐI (TEST CONNECTION) ---
if __name__ == "__main__":
    import time
    print("⏳ Đang thử kết nối đến Azure SQL Server...")
    print(f"   IP: {SERVER} | DB: {DATABASE}")
    
    try:
        # Thử kết nối và query phiên bản SQL
        with engine.connect() as connection:
            start_time = time.time()
            result = connection.execute(text("SELECT @@VERSION"))
            version = result.fetchone()[0]
            end_time = time.time()
            
            print("\n" + "="*40)
            print("✅ KẾT NỐI THÀNH CÔNG! (Success)")
            print("="*40)
            print(f"⏱️ Thời gian phản hồi: {round(end_time - start_time, 2)}s")
            print(f"📌 Phiên bản SQL: {version.split(' - ')[0]}") # In tên bản SQL cho gọn
            print("="*40 + "\n")
            
    except Exception as e:
        print("\n" + "x"*40)
        print("❌ KẾT NỐI THẤT BẠI! (Failed)")
        print("x"*40)
        print(f"Lỗi chi tiết: {e}")
        print("x"*40 + "\n")