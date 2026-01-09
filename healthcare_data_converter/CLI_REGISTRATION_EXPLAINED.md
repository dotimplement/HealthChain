# Cơ chế đăng ký CLI Command: healthcare-converter

## Tổng quan

Command `healthcare-converter` được đăng ký thông qua **Python Entry Points** trong file `pyproject.toml`.

## 1. Định nghĩa Entry Point

Trong file `pyproject.toml`, có section `[project.scripts]`:

```toml
[project.scripts]
healthcare-converter = "healthcare_data_converter.cli:main"
```

**Giải thích:**
- `healthcare-converter`: Tên command sẽ được tạo trong terminal
- `healthcare_data_converter.cli:main`: Đường dẫn đến function
  - `healthcare_data_converter.cli`: Module path (file `cli.py`)
  - `main`: Function name trong file `cli.py`

## 2. Khi nào command được tạo?

Command được tạo tự động khi bạn chạy:

```bash
pip install -e .
```

**Quá trình:**
1. `pip` đọc `pyproject.toml`
2. Tìm section `[project.scripts]`
3. Tạo script wrapper trong `venv/bin/` (hoặc system bin nếu install global)
4. Script wrapper sẽ gọi function `main()` từ `cli.py`

## 3. Vị trí script được tạo

### Trong virtual environment:
```
venv/bin/healthcare-converter
```

### Nội dung script (tự động tạo):
```bash
#!/path/to/venv/bin/python
# -*- coding: utf-8 -*-
import re
import sys
from healthcare_data_converter.cli import main

if __name__ == '__main__':
    sys.exit(main())
```

## 4. Cấu trúc CLI

### File: `cli.py`

```python
def main():
    """Main entry point."""
    args = parse_args()  # Parse command line arguments
    
    commands = {
        "convert": cmd_convert,
        "validate": cmd_validate,
        "serve": cmd_serve,
        "info": cmd_info,
        "batch": cmd_batch,
    }
    
    return commands[args.command](args)  # Execute command
```

### Flow hoạt động:

```
Terminal: healthcare-converter convert -i file.xml
    ↓
Script: venv/bin/healthcare-converter
    ↓
Python: healthcare_data_converter.cli.main()
    ↓
Parse args: parse_args() → args.command = "convert"
    ↓
Execute: cmd_convert(args)
    ↓
Result: Return exit code
```

## 5. Kiểm tra command đã được đăng ký

### Cách 1: Kiểm tra file script
```bash
ls -la venv/bin/healthcare-converter
cat venv/bin/healthcare-converter
```

### Cách 2: Kiểm tra PATH
```bash
which healthcare-converter
```

### Cách 3: Test command
```bash
healthcare-converter --help
```

## 6. Các loại Entry Points

### `[project.scripts]` - Console Scripts
- Tạo command line tools
- Có thể gọi trực tiếp từ terminal
- Ví dụ: `healthcare-converter`, `pip`, `pytest`

### `[project.entry-points]` - Plugin Entry Points
- Dùng cho plugins/extensions
- Không tạo command line tools

## 7. Ví dụ thực tế

### Trước khi install:
```bash
$ healthcare-converter
zsh: command not found: healthcare-converter
```

### Sau khi `pip install -e .`:
```bash
$ healthcare-converter --help
Usage: healthcare-converter <command> [options]
Commands: convert, validate, serve, info, batch
...
```

## 8. Troubleshooting

### Command không tìm thấy:
1. **Kiểm tra đã install chưa:**
   ```bash
   pip list | grep healthcare-data-converter
   ```

2. **Kiểm tra virtual environment:**
   ```bash
   which python
   source venv/bin/activate
   ```

3. **Reinstall:**
   ```bash
   pip uninstall healthcare-data-converter
   pip install -e .
   ```

### Command không hoạt động:
1. **Kiểm tra function main() có tồn tại:**
   ```bash
   python -c "from healthcare_data_converter.cli import main; print(main)"
   ```

2. **Kiểm tra script permissions:**
   ```bash
   chmod +x venv/bin/healthcare-converter
   ```

## 9. So sánh với các package khác

### pip (từ setuptools):
```toml
[project.scripts]
pip = "pip._internal.cli.main:main"
```

### pytest:
```toml
[project.scripts]
pytest = "pytest:main"
```

### uvicorn:
```toml
[project.scripts]
uvicorn = "uvicorn.main:main"
```

## 10. Tóm tắt

| Bước | Mô tả | File liên quan |
|------|-------|----------------|
| 1 | Định nghĩa entry point | `pyproject.toml` |
| 2 | Implement function | `cli.py` → `main()` |
| 3 | Install package | `pip install -e .` |
| 4 | Script được tạo | `venv/bin/healthcare-converter` |
| 5 | Sử dụng | `healthcare-converter --help` |

## 11. Code Flow Diagram

```
┌─────────────────────────────────────┐
│  pyproject.toml                     │
│  [project.scripts]                  │
│  healthcare-converter = ...          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  pip install -e .                    │
│  (Build system: hatchling)           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  venv/bin/healthcare-converter       │
│  (Script wrapper tự động tạo)        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  healthcare_data_converter.cli.main()│
│  (Function thực tế)                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Parse args → Execute command        │
│  (convert, validate, serve, etc.)    │
└─────────────────────────────────────┘
```

## 12. Kiểm tra thực tế

Chạy các lệnh sau để xem chi tiết:

```bash
# Xem script được tạo
cat venv/bin/healthcare-converter

# Xem entry points đã đăng ký
pip show healthcare-data-converter

# Test import
python -c "from healthcare_data_converter.cli import main; print('✓ Function found')"
```

