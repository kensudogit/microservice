from flask import Flask, request, jsonify, send_from_directory
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import jwt
from jwt import InvalidTokenError
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime
import os
from typing import Any, Dict

app = Flask(__name__)
CORS(app)  # CORSを有効にする

# Oracleデータベースの設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'oracle+cx_oracle://username:password@host:port/?service_name=your_service_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# アップロードフォルダの設定
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 認証デコレーター
def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or not verify_token(auth):
            return jsonify({"message": "認証に失敗しました"}), 401
        return f(*args, **kwargs)
    return decorated_function

# トークンの検証
def verify_token(token):
    secret_key = 'your_secret_key'  # ここに実際のシークレットキーを設定

    try:
        # トークンをデコードしてペイロードを取得
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        # トークンが有効であればTrueを返す
        return True
    except InvalidTokenError:
        # トークンが無効であればFalseを返す
        return False

# 認証されたデータの取得
@app.route('/secure-data', methods=['GET'])
@authenticate
def get_secure_data():
    return jsonify({"message": "認証されたデータにアクセスしました"})

# 物件モデルの定義
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

# 取引先金融機関モデル
class FinancialInstitution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(100), nullable=False)

# JV・提携先モデル
class JVPartner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    partnership_type = db.Column(db.String(100), nullable=False)

# ドキュメントのバージョン管理モデル
class DocumentVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, nullable=False)
    document_name = db.Column(db.String(255), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    __table_args__ = (
        db.UniqueConstraint('transaction_id', 'document_name', 'version_number', name='unique_version'),
    )

# データベースの初期化
@app.before_first_request
def create_tables():
    db.create_all()

# 物件情報の取得
@app.route('/api/property', methods=['GET'])
def get_properties():
    # ダミーデータを返す
    properties = [
        {"id": 1, "name": "Property 1", "location": "Location 1", "price": 100000},
        {"id": 2, "name": "Property 2", "location": "Location 2", "price": 150000}
    ]
    return jsonify(properties)

# 物件情報の登録
@app.route('/property', methods=['POST'])
def add_property():
    data = request.json
    new_property = Property(name=data['name'], location=data['location'], price=data['price'])
    db.session.add(new_property)
    db.session.commit()
    return jsonify({"message": "物件情報を登録しました"})

# 電子契約の処理
@app.route('/contract', methods=['POST'])
def handle_contract():
    data = request.json
    # ここで電子契約の処理を実装
    return jsonify({"message": "電子契約を処理しました"})

# 取引先金融機関の取得
@app.route('/api/financial_institutions', methods=['GET'])
def get_financial_institutions():
    institutions = FinancialInstitution.query.all()
    return jsonify([{"id": inst.id, "name": inst.name, "branch": inst.branch} for inst in institutions])

# 取引先金融機関の登録
@app.route('/api/financial_institution', methods=['POST'])
def add_financial_institution():
    data = request.json
    new_institution = FinancialInstitution(name=data['name'], branch=data['branch'])
    db.session.add(new_institution)
    db.session.commit()
    return jsonify({"message": "取引先金融機関を登録しました"})

# JV・提携先の取得
@app.route('/api/jv_partners', methods=['GET'])
def get_jv_partners():
    partners = JVPartner.query.all()
    return jsonify([{"id": partner.id, "name": partner.name, "partnership_type": partner.partnership_type} for partner in partners])

# JV・提携先の登録
@app.route('/api/jv_partner', methods=['POST'])
def add_jv_partner():
    data = request.json
    new_partner = JVPartner(name=data['name'], partnership_type=data['partnership_type'])
    db.session.add(new_partner)
    db.session.commit()
    return jsonify({"message": "JV・提携先を登録しました"})

class TransactionWorkflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, nullable=False)
    stage = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route('/api/workflow/<int:transaction_id>', methods=['GET'])
def get_workflow(transaction_id):
    workflow = TransactionWorkflow.query.filter_by(transaction_id=transaction_id).all()
    return jsonify([{"stage": w.stage, "status": w.status, "updated_at": w.updated_at} for w in workflow])

@app.route('/api/workflow', methods=['POST'])
def update_workflow():
    data = request.json
    transaction_id = data['transaction_id']
    stage = data['stage']
    status = data['status']

    # Update or create a new workflow stage
    workflow = TransactionWorkflow.query.filter_by(transaction_id=transaction_id, stage=stage).first()
    if workflow:
        workflow.status = status
        workflow.updated_at = db.func.current_timestamp()
    else:
        workflow = TransactionWorkflow(transaction_id=transaction_id, stage=stage, status=status)
        db.session.add(workflow)

    db.session.commit()
    return jsonify({"message": "Workflow updated successfully"})

class NegotiationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route('/api/negotiation_records/<int:case_id>', methods=['GET'])
def get_negotiation_records(case_id):
    records = NegotiationRecord.query.filter_by(case_id=case_id).all()
    return jsonify([{"id": record.id, "details": record.details, "status": record.status, "updated_at": record.updated_at} for record in records])

@app.route('/api/negotiation_case/<int:case_id>/status', methods=['POST'])
def update_negotiation_case_status(case_id):
    data = request.json
    new_status = data['status']  # Expected values: 'approved', 'rejected', 'returned', 'withdrawn'

    # Update the status of the negotiation case
    record = NegotiationRecord.query.filter_by(case_id=case_id).first()
    if record:
        record.status = new_status
        record.updated_at = db.func.current_timestamp()
        db.session.commit()
        return jsonify({"message": f"Negotiation case status updated to {new_status}"})
    else:
        return jsonify({"message": "Negotiation case not found"}), 404

class IncomeStatement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, nullable=False)
    revenue = db.Column(db.Float, nullable=False)
    expenses = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class BalanceSheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_assets = db.Column(db.Float, nullable=False)
    total_liabilities = db.Column(db.Float, nullable=False)
    equity = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route('/api/income_statement/<int:case_id>', methods=['GET'])
def get_income_statement(case_id):
    statement = IncomeStatement.query.filter_by(case_id=case_id).first()
    if statement:
        return jsonify({
            "case_id": statement.case_id,
            "revenue": statement.revenue,
            "expenses": statement.expenses,
            "profit": statement.profit,
            "created_at": statement.created_at
        })
    else:
        return jsonify({"message": "Income statement not found"}), 404

@app.route('/api/income_statement', methods=['POST'])
def create_income_statement():
    data = request.json
    revenue = data['revenue']
    expenses = data['expenses']
    profit = revenue - expenses
    case_id = data['case_id']

    new_statement = IncomeStatement(case_id=case_id, revenue=revenue, expenses=expenses, profit=profit)
    db.session.add(new_statement)
    db.session.commit()
    return jsonify({"message": "Income statement created successfully"})

@app.route('/api/balance_sheet', methods=['GET'])
def get_balance_sheet():
    balance_sheet = BalanceSheet.query.order_by(BalanceSheet.created_at.desc()).first()
    if balance_sheet:
        return jsonify({
            "total_assets": balance_sheet.total_assets,
            "total_liabilities": balance_sheet.total_liabilities,
            "equity": balance_sheet.equity,
            "created_at": balance_sheet.created_at
        })
    else:
        return jsonify({"message": "Balance sheet not found"}), 404

@app.route('/api/balance_sheet', methods=['POST'])
def create_balance_sheet():
    data = request.json
    total_assets = data['total_assets']
    total_liabilities = data['total_liabilities']
    equity = total_assets - total_liabilities

    new_balance_sheet = BalanceSheet(total_assets=total_assets, total_liabilities=total_liabilities, equity=equity)
    db.session.add(new_balance_sheet)
    db.session.commit()
    return jsonify({"message": "Balance sheet created successfully"})

# Generate RSA keys
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

# Serialize private key
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)

# Serialize public key
public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Save keys to files or secure storage
with open("private_key.pem", "wb") as f:
    f.write(private_pem)

with open("public_key.pem", "wb") as f:
    f.write(public_pem)

def sign_data(data, private_key_path):
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )

    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature

def verify_signature(data, signature, public_key_path):
    with open(public_key_path, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read()
        )

    try:
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        return False

def get_timestamp():
    return datetime.utcnow().isoformat()

@app.route('/api/document_version', methods=['POST'])
def create_document_version():
    data = request.json
    transaction_id = data['transaction_id']
    document_name = data['document_name']
    content = data['content']

    # Determine the next version number
    latest_version = DocumentVersion.query.filter_by(transaction_id=transaction_id, document_name=document_name).order_by(DocumentVersion.version_number.desc()).first()
    next_version_number = 1 if not latest_version else latest_version.version_number + 1

    new_version = DocumentVersion(
        transaction_id=transaction_id,
        document_name=document_name,
        version_number=next_version_number,
        content=content
    )
    db.session.add(new_version)
    db.session.commit()
    return jsonify({"message": "Document version created successfully", "version_number": next_version_number})

@app.route('/api/document_versions/<int:transaction_id>/<string:document_name>', methods=['GET'])
def get_document_versions(transaction_id, document_name):
    versions = DocumentVersion.query.filter_by(transaction_id=transaction_id, document_name=document_name).order_by(DocumentVersion.version_number).all()
    return jsonify([{
        "version_number": version.version_number,
        "content": version.content,
        "created_at": version.created_at
    } for version in versions])

# ドキュメントのアップロード
@app.route('/api/upload_document', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400

    transaction_id = request.form.get('transaction_id')
    document_name = request.form.get('document_name')

    # ファイルを保存
    filename = f"{transaction_id}_{document_name}_{file.filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    return jsonify({"message": "File uploaded successfully", "filename": filename})

# ドキュメントのダウンロード
@app.route('/api/download_document/<filename>', methods=['GET'])
def download_document(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"message": "File not found"}), 404

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Your code here
    return {
        'statusCode': 200,
        'body': 'Hello from Lambda!'
    }

if __name__ == '__main__':
    app.run(debug=True)
