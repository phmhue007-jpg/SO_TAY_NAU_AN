from flask import Flask, render_template, request, redirect, url_for, session 
from flask_sqlalchemy import SQLAlchemy 
# Sử dụng thư viện bảo mật có sẵn của Werkzeug để mã hóa mật khẩu
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename

app = Flask(__name__) 
# Kết nối database và config session 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cooking.db" 
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False 

# Secret key để dùng session, đặt dài một chuỗi random cho bảo mật 
app.config["SECRET_KEY"] = "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1" 

db = SQLAlchemy(app)

# Cho vào thư mục static/uploads
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Chỉ cho up mấy đuôi ảnh này thôi
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Nếu chưa có thư mục thì tự tạo mới
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Hàm check xem file có đúng đuôi ảnh không
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# tạo bảng trong CSDL
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # nâng cấp lưu chuỗi băm bảo mật
    role = db.Column(db.String(20), default="user")
    # Thiết lập mối quan hệ ngược từ User đến Recipe
    recipes = db.relationship('Recipe', backref='author', lazy=True)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)        
    ingredients = db.Column(db.Text, nullable=False)         
    instructions = db.Column(db.Text, nullable=False)        
    image_url = db.Column(db.String(300), default="https://images.unsplash.com/photo-1495521821757-a1efb6729352") 
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 

# HỆ THỐNG (ROUTES)

# trang chủ và tìm kiếm
@app.route("/")
def home():
    # Lấy từ khóa search từ ô tìm kiếm
    query = request.args.get("search")
    
    if query:
        # Tìm kiếm theo tên hoặc nguyên liệu
        recipes = Recipe.query.filter(
            Recipe.title.icontains(query) | Recipe.ingredients.icontains(query)
        ).all()
    else:
        # Còn không thì lấy hết tất cả recipe ra
        recipes = Recipe.query.all()
        
    return render_template("index.html", recipes=recipes, search_query=query)

# chi tiết công thức nấu ăn
@app.route("/recipe/<int:id>", methods=["GET"])
def recipe_detail(id):
    recipe = Recipe.query.get_or_404(id)
    return render_template("detail.html", recipe=recipe)
# đánh giá thích
@app.route("/recipe/<int:id>/like")
def like_recipe(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    recipe = Recipe.query.get_or_404(id)
    recipe.likes += 1
    db.session.commit()
    return redirect(url_for("recipe_detail", id=id))

# đánh giá không thích
@app.route("/recipe/<int:id>/dislike")
def dislike_recipe(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    recipe = Recipe.query.get_or_404(id)
    recipe.dislikes += 1
    db.session.commit()
    return redirect(url_for("recipe_detail", id=id))

# đăng ký
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]  
        
        hashed_password = generate_password_hash(password, method='scrypt')
        
        role = "admin" if username.lower() == "admin" else "user"
        try:
            # Tạo user mới với mật khẩu đã mã hóa và lưu vào DB
            new_user = User(username=username, password=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login"))
        except:
            return "Tên đăng nhập đã tồn tại!"
    return render_template("register.html")

# đăng nhập
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role 
            return redirect(url_for("home"))
        return "Sai tài khoản hoặc mật khẩu!"
    return render_template("login.html")

# đăng xuất
@app.route("/logout")
def logout():
    session.clear()  # Log out thì clear hết session luôn
    return redirect(url_for("home"))

# thêm công thức
@app.route("/add", methods=["GET", "POST"])
def add_recipe():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    if request.method == "POST":
        title = request.form["title"]
        ingredients = request.form["ingredients"]
        instructions = request.form["instructions"]
        
        # Mặc định nếu không up ảnh thì lấy ảnh này
        image_url = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c" 
        
        # Lấy file từ form gửi lên
        file = request.files.get("image_file")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Lưu file vào thư mục static/uploads
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Đường dẫn để vào HTML hiển thị được
            image_url = url_for('static', filename='uploads/' + filename)
            
        new_recipe = Recipe(
            title=title, 
            ingredients=ingredients, 
            instructions=instructions, 
            image_url=image_url,
            user_id=session["user_id"]
        )
        db.session.add(new_recipe)
        db.session.commit()
        return redirect(url_for("home"))
        
    return render_template("add.html")

# sửa công thức
@app.route("/update/<int:id>", methods=["GET", "POST"])
def update_recipe(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    recipe = Recipe.query.get_or_404(id)
    
    if recipe.user_id and recipe.user_id != session.get("user_id") and session.get("role") != "admin":
        return "Bạn không có quyền chỉnh sửa công thức của người khác!", 403
        
    if request.method == "POST":
        recipe.title = request.form["title"]
        recipe.ingredients = request.form["ingredients"]
        recipe.instructions = request.form["instructions"]
        
        # Check xem user có up ảnh mới không, nếu có thì ghi đè ảnh cũ
        file = request.files.get("image_file")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            recipe.image_url = url_for('static', filename='uploads/' + filename)
            
        db.session.commit()
        return redirect(url_for("home"))
        
    return render_template("update.html", recipe=recipe)

# xóa công thức nấu ăn
@app.route("/delete/<int:id>")
def delete_recipe(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    recipe = Recipe.query.get_or_404(id)
  
    if recipe.user_id and recipe.user_id != session.get("user_id") and session.get("role") != "admin":
        return "Bạn không có quyền xóa công thức của người khác!", 403
        
    db.session.delete(recipe)
    db.session.commit()
    return redirect(url_for("home"))

# quản trị viên: quản lúy tài khoản người dùng
@app.route("/admin/users")
def manage_users():
    if session.get("role") != "admin":
        return "Bạn không có quyền truy cập trang này!", 403
    
    users = User.query.all()
    return render_template("manage_users.html", users=users)

# quản trị viên: xóa tài khoản
@app.route("/admin/users/delete/<int:id>")
def delete_user(id):
    if session.get("role") != "admin":
        return "Bạn không có quyền thực hiện!", 403
        
    user = User.query.get_or_404(id)
    if user.username.lower() == "admin":
        return "Không thể xóa tài khoản Admin", 400
        
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("manage_users"))

# quản trị viên: phân quyền hệ thống
@app.route("/admin/users/change_role/<int:id>", methods=["POST"])
def change_user_role(id):
    if session.get("role") != "admin":
        return "Bạn không có quyền thực hiện!", 403
        
    user = User.query.get_or_404(id)
    if user.username.lower() == "admin":
        return "Không thể đổi quyền của Admin", 400
        
    new_role = request.form.get("role")
    if new_role in ["user", "admin"]:
        user.role = new_role
        db.session.commit()
        
    return redirect(url_for("manage_users"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Tự động tạo bảng nếu chưa có db
            
    app.run(debug=True, use_reloader=False, port=8080)