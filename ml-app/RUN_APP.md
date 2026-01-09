# Hướng dẫn chạy ML App

## Bước 1: Cài đặt dependencies

Chạy trong terminal (sandbox không có network access):

```bash
cd /Users/huy/Code/fpt/care-chain

# Cài đặt dependencies
pip install scikit-learn joblib python-dotenv 'python-jose[cryptography]' python-multipart pydantic-settings
```

## Bước 2: File .env đã được tạo

File `.env` đã được tạo với các giá trị mặc định. Bạn có thể chỉnh sửa nếu cần.

## Bước 3: Train demo model

```bash
python ml-app/train_demo_model.py
```

Script này sẽ:
- Tạo synthetic healthcare data
- Train Random Forest model
- Lưu model vào `ml-app/models/model.pkl`

## Bước 4: Chạy app

```bash
python ml-app/app.py
```

App sẽ chạy tại: http://localhost:8000

## Bước 5: Test endpoints

Mở terminal mới và chạy:

```bash
# Health check
curl http://localhost:8000/health

# Model info
curl http://localhost:8000/model/info

# CDS Services discovery
curl http://localhost:8000/cds/cds-services
```

## Lưu ý

- Đảm bảo port 8000 không bị chiếm bởi process khác
- Nếu cần OAuth2, chỉnh sửa `.env` và set `OAUTH2_ENABLED=true`
- Xem API docs tại: http://localhost:8000/docs

