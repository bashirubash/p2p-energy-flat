from flask import Flask, request, redirect, session, flash, render_template_string, url_for
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
app.secret_key = 'yedc_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
db = SQLAlchemy(app)

# ---- Models ----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    meter_number = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(10))

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    units = db.Column(db.Integer)
    price_eth = db.Column(db.Float)
    band = db.Column(db.String(10))
    status = db.Column(db.String(20), default="Available")
    buyer_meter = db.Column(db.String(100), nullable=True)
    buyer_email = db.Column(db.String(100), nullable=True)
    transaction_status = db.Column(db.String(20), default="Pending")

# ---- Initialize DB ----
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email="gurus@gmail.com").first():
        admin = User(name="Guru", meter_number="0000", email="gurus@gmail.com", password="Guru123", role="admin")
        db.session.add(admin)
        for i in range(50):
            band = random.choice(['A', 'B', 'C', 'D'])
            db.session.add(Unit(units=1, price_eth=0.0005, band=band))
        db.session.commit()

# ---- Routes ----
@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        meter = request.form['meter']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            flash('Passwords do not match')
            return redirect('/register')
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect('/register')
        db.session.add(User(name=name, meter_number=meter, email=email, password=password, role='buyer'))
        db.session.commit()
        session['user'] = email
        session['role'] = 'buyer'
        session['meter'] = meter
        return redirect('/welcome')
    return render_template_string(register_html)

@app.route('/welcome')
def welcome():
    if 'user' not in session:
        return redirect('/login')
    return render_template_string(welcome_html, meter=session['meter'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user'] = user.email
            session['role'] = user.role
            session['meter'] = user.meter_number
            return redirect('/dashboard')
        flash('Invalid credentials')
    return render_template_string(login_html)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    role = session['role']
    if role == 'admin':
        units = Unit.query.offset(offset).limit(per_page).all()
        total_units = Unit.query.count()
    else:
        units = Unit.query.filter_by(status='Available').offset(offset).limit(per_page).all()
        total_units = Unit.query.filter_by(status='Available').count()

    next_page = page + 1 if offset + per_page < total_units else None
    prev_page = page - 1 if page > 1 else None

    return render_template_string(dashboard_html, units=units, role=role, meter=session['meter'],
                                  page=page, next_page=next_page, prev_page=prev_page)

@app.route('/add_unit', methods=['POST'])
def add_unit():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    units = int(request.form['units'])
    price = float(request.form['price'])
    band = request.form['band']
    db.session.add(Unit(units=units, price_eth=price, band=band))
    db.session.commit()
    flash('Unit listed successfully')
    return redirect('/dashboard')

@app.route('/buy/<int:unit_id>')
def buy(unit_id):
    if session.get('role') != 'buyer':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    if unit.status != 'Available':
        flash('Unit not available.')
    else:
        unit.status = 'Pending'
        unit.buyer_meter = session['meter']
        unit.buyer_email = session['user']
        db.session.commit()
        flash(f'Unit purchased! Admin will verify and credit your meter: {session["meter"]}')
    return redirect('/dashboard')

@app.route('/pending')
def pending():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    pending_units = Unit.query.filter_by(status='Pending').all()

    # Auto-generate fake pending transactions for demo if not enough
    if len(pending_units) < 10:
        for i in range(10 - len(pending_units)):
            u = Unit(units=1, price_eth=0.0005, band=random.choice(['A','B','C','D']), status='Pending',
                     buyer_meter='1000'+str(i), buyer_email=f'user{i}@demo.com')
            db.session.add(u)
        db.session.commit()
        pending_units = Unit.query.filter_by(status='Pending').all()

    return render_template_string(pending_html, units=pending_units[:10])

@app.route('/complete')
def complete():
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    complete_units = Unit.query.filter_by(status='Sold').all()
    return render_template_string(complete_html, units=complete_units)

@app.route('/release/<int:unit_id>')
def release(unit_id):
    if session.get('role') != 'admin':
        return redirect('/dashboard')
    unit = Unit.query.get(unit_id)
    unit.status = 'Sold'
    unit.transaction_status = 'Paid'
    db.session.commit()
    flash(f'Unit credited to meter {unit.buyer_meter}')
    return redirect('/pending')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---- HTML Templates ----

# (REUSE THE SAME register_html, login_html, welcome_html FROM PREVIOUS RESPONSE)

dashboard_html = """
<!DOCTYPE html><html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body><div class="container-fluid">
<div class="row">
<div class="col-2 bg-dark text-white p-3" style="min-height:100vh;">
<h4>YEDC Panel</h4>
{% if role == 'admin' %}
<a href="/dashboard" class="d-block text-white mb-2">Listings</a>
<a href="/pending" class="d-block text-white mb-2">Pending</a>
<a href="/complete" class="d-block text-white mb-2">Completed</a>
{% endif %}
<a href="/logout" class="d-block text-white mt-4">Logout</a>
</div>

<div class="col-10 p-4">
<h3>Dashboard - {{ role|capitalize }}</h3>
{% with messages = get_flashed_messages() %}
{% if messages %}<div class="alert alert-info">{{ messages[0] }}</div>{% endif %}
{% endwith %}

{% if role == 'admin' %}
<form method="POST" action="/add_unit" class="row my-3">
<div class="col"><input name="units" class="form-control" placeholder="Units" required></div>
<div class="col"><input name="price" class="form-control" placeholder="Price ETH" required></div>
<div class="col"><select name="band" class="form-control"><option>A</option><option>B</option><option>C</option><option>D</option></select></div>
<div class="col"><button class="btn btn-primary">Add</button></div>
</form>
{% endif %}

<div class="row">
{% for u in units %}
<div class="col-md-3 border p-2 m-1 text-center">
<b>{{ u.units }}</b> Units<br>{{ u.price_eth }} ETH<br>Band: {{ u.band }}<br>{{ u.status }}<br>
{% if role=='buyer' and u.status == 'Available' %}
<a href="/buy/{{ u.id }}" class="btn btn-sm btn-success mt-1">Buy</a>
{% else %}-{% endif %}
</div>
{% endfor %}
</div>

<div class="mt-4">
{% if prev_page %}
<a href="{{ url_for('dashboard', page=prev_page) }}" class="btn btn-secondary">Previous</a>
{% endif %}
{% if next_page %}
<a href="{{ url_for('dashboard', page=next_page) }}" class="btn btn-primary">Next</a>
{% endif %}
</div>

</div></div></div>
<footer class="bg-dark text-white text-center p-3 mt-5"><small>© 2025 YEDC Energy Portal</small></footer>
</body></html>
"""

pending_html = """
<!DOCTYPE html><html><head><title>Pending</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Pending Transactions</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Meter</th><th>Email</th><th>Band</th><th>Action</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.buyer_meter }}</td><td>{{ u.buyer_email }}</td><td>{{ u.band }}</td>
<td><a href="/release/{{ u.id }}" class="btn btn-primary btn-sm">Release</a></td></tr>
{% endfor %}
</table></div>
<footer class="bg-dark text-white text-center p-3 mt-5"><small>© 2025 YEDC Energy Portal</small></footer>
</body></html>
"""

complete_html = """
<!DOCTYPE html><html><head><title>Completed</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body>
<div class="container mt-5"><h3>Completed Transactions</h3>
<table class="table table-bordered">
<tr><th>ID</th><th>Units</th><th>Price</th><th>Meter</th><th>Email</th><th>Band</th></tr>
{% for u in units %}
<tr><td>{{ u.id }}</td><td>{{ u.units }}</td><td>{{ u.price_eth }}</td><td>{{ u.buyer_meter }}</td><td>{{ u.buyer_email }}</td><td>{{ u.band }}</td></tr>
{% endfor %}
</table></div>
<footer class="bg-dark text-white text-center p-3 mt-5"><small>© 2025 YEDC Energy Portal</small></footer>
</body></html>
"""

# ---- Run ----
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
