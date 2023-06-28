from flask import Flask, render_template, request, redirect, url_for, flash
from flaskext.mysql import MySQL
from datetime import datetime
import os
from flask import jsonify
from flask import send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required


app = Flask(__name__)
app.secret_key = 'mi_clave_secreta_super_secreta'



mysql = MySQL()
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'sistema'
mysql.init_app(app)

CARPETA= os.path.join('uploads')
app.config['CARPETA']=CARPETA

# Configuración del login manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Modelo de usuario para el login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/uploads/<nombreFoto>')
def uploads(nombreFoto):
    return send_from_directory(app.config['CARPETA'], nombreFoto)


@app.route('/', methods=['GET'])
@login_required
def index():
    conn = mysql.connect()
    cursor = conn.cursor()

    # Obtener los términos de búsqueda del formulario
    query = request.args.get('query', '')

    if query:
        # Filtrar empleados según los términos de búsqueda
        sql = "SELECT * FROM empleados WHERE nombre LIKE %s OR correo LIKE %s;"
        params = ('%' + query + '%', '%' + query + '%')
        cursor.execute(sql, params)
    else:
        # Obtener todos los empleados si no se proporcionan términos de búsqueda
        sql = "SELECT * FROM empleados;"
        cursor.execute(sql)

    empleados = cursor.fetchall()

    # Obtener la lista de departamentos
    cursor.execute("SELECT * FROM departamentos;")
    departamentos = cursor.fetchall()

    conn.close()

    return render_template('empleados/index.html', empleados=empleados, departamentos=departamentos, query=query)



    
@app.route('/destroy/<int:id>')
@login_required
def destroy(id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT foto FROM empleados WHERE id=%s", id)

    fila=cursor.fetchall()
    os.remove(os.path.join(app.config['CARPETA'], fila[0][0]))
    cursor.execute("DELETE FROM empleados WHERE id=%s", (id))
    conn.commit()
    
   
    return redirect('/')  # Redirige a la página que muestra la lista de empleados

@app.route('/edit/<int:id>')
@login_required
def edit(id):

    conn= mysql.connect()
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM empleados WHERE id=%s", (id)) 
    empleados=cursor.fetchall() 
    conn.commit()
    return render_template('empleados/edit.html', empleados=empleados)
  
@app.route('/update', methods=['POST'])
@login_required
def update():
    _correo = request.form['email']
    _id = request.form['ID']
    _departamento_id = request.form['departamento_id']

    conn = mysql.connect()
    cursor = conn.cursor()

    # Actualizar el campo 'departamento_id' del empleado en la base de datos
    sql = "UPDATE empleados SET departamento_id=%s WHERE id=%s;"
    datos = (_departamento_id, _id)
    cursor.execute(sql, datos)
    conn.commit()

    conn.close()

    return redirect('/')



@app.route('/create')
@login_required
def create():
    conn = mysql.connect()
    cursor = conn.cursor()

    # Obtener departamentos
    cursor.execute("SELECT * FROM departamentos")
    departamentos = cursor.fetchall()

    conn.close()

    return render_template('empleados/create.html', departamentos=departamentos)


@app.route('/store', methods=['POST'])
@login_required
def storage():
    _nombre = request.form['nombre']
    _correo = request.form['email']
    _foto = request.files['foto']

    now= datetime.now()
    tiempo=now.strftime("%Y%H%M%S")

    if _foto.filename!='':
        nuevoNombreFoto=tiempo+_foto.filename

         # Guardar la foto en el sistema de archivos
        _foto.save("uploads/" + nuevoNombreFoto)   

    # Insertar datos en la base de datos
    sql = "INSERT INTO `empleados` (`id`, `nombre`, `correo`, `foto`) VALUES (NULL, %s, %s, %s);"
    
    datos = (_nombre, _correo, nuevoNombreFoto)
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute(sql, datos)
    conn.commit()  

    return redirect('/')

@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    conn = mysql.connect()
    cursor = conn.cursor()

    if request.method == 'POST':
        empleado_id = request.form.get('empleado_id')
        accion = request.form.get('accion')

        if accion == 'eliminar':
            # Eliminar el departamento asignado del empleado
            sql = "UPDATE empleados SET departamento_id=NULL WHERE id=%s;"
            cursor.execute(sql, (empleado_id,))
            conn.commit()
            flash('Departamento eliminado del empleado', 'success')

    # Obtener empleados asignados a departamentos junto con el nombre del departamento
    cursor.execute("SELECT empleados.*, departamentos.nombre AS departamento FROM empleados LEFT JOIN departamentos ON empleados.departamento_id = departamentos.id WHERE empleados.departamento_id IS NOT NULL;")
    empleados_departamentos = cursor.fetchall()

    conn.close()

    return render_template('empleados/cart.html', empleados_departamentos=empleados_departamentos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Verificar las credenciales del usuario
        if username == 'admin' and password == 'admin123':
            # Crear un objeto User y registrar la sesión del usuario
            user = User(1)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Credenciales inválidas', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # Cerrar sesión del usuario actual
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Obtener los datos del formulario de registro
        username = request.form.get('username')
        password = request.form.get('password')

        # Validar y crear el nuevo usuario
        # ...

        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/api/empleados', methods=['GET'])
def get_empleados():
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT empleados.*, departamentos.nombre AS departamento FROM empleados LEFT JOIN departamentos ON empleados.departamento_id = departamentos.id")
    empleados = cursor.fetchall()
    conn.close()

    # Convertir la lista de empleados a formato JSON y retornarla
    empleados_json = []
    for empleado in empleados:
        empleado_dict = {
            'id': empleado[0],
            'nombre': empleado[1],
            'correo': empleado[2],
            'foto': empleado[3],
            'departamento': empleado[5]  # Agregamos el nombre del departamento
        }
        empleados_json.append(empleado_dict)

    return jsonify(empleados_json)


@app.route('/api/empleados/<int:id>', methods=['PUT'])
def update_empleado(id):
    _nombre = request.form['nombre']
    _correo = request.form['correo']

    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE empleados SET nombre=%s, correo=%s WHERE id=%s", (_nombre, _correo, id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Empleado actualizado correctamente'})


@app.route('/api/empleados', methods=['POST'])
def create_empleado():
    _nombre = request.form['nombre']
    _correo = request.form['correo']

    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO empleados (nombre, correo) VALUES (%s, %s)", (_nombre, _correo))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Empleado creado correctamente'})


@app.route('/api/empleados/<int:id>', methods=['DELETE'])
def delete_empleado(id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM empleados WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Empleado eliminado correctamente'})


if __name__ == '__main__':
    app.run(debug=True)
