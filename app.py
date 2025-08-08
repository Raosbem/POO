from flask import Flask, render_template, request, redirect, session, url_for, flash, abort
import pyodbc
import re
from werkzeug.utils import secure_filename
import os

EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PASSWORD_REGEX = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,64}$'
)

ALLOWED_ROLES = {'ASPIRANTE', 'ADMIN', 'RECLUTADOR'}

app = Flask(__name__)
app.secret_key = 'clave_secreta_upq'

UPLOAD_FOLDER = 'static/profile_pics'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=ANTHONY-RAMOS\\SQLEXPRESS;'
        'DATABASE=BolsaTrabajoUPQ;'
        'Trusted_Connection=yes;'
    )

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo'].strip()
        contrasena = request.form['contrasena'].strip()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT U.id_usuario, U.correo, U.rol, A.id_aspirante
            FROM Usuarios U
            LEFT JOIN Aspirantes A ON A.id_usuario = U.id_usuario
            WHERE U.correo=? AND U.contrasena=? AND U.activo=1
        """, (correo, contrasena))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            session['usuario'] = {
                'id': row.id_usuario,
                'correo': row.correo,
                'rol': row.rol,
                'id_aspirante': row.id_aspirante
            }

            if row.rol == 'CANDIDATO':
                return redirect(url_for('perfil_candidato'))
            elif row.rol == 'ADMINISTRADOR':
                return redirect(url_for('dashboard_admin'))
            else:
                flash('Rol desconocido. Contacta al administrador.', 'warning')
                return redirect(url_for('login'))
        else:
            flash('Credenciales incorrectas o cuenta inactiva', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/registrarse', methods=['GET', 'POST'])
def registrarse():
    if request.method == 'POST':
        correo = request.form['correo'].strip()
        contrasena = request.form['contrasena'].strip()
        rol = request.form['rol'].strip()

        if rol not in ['CANDIDATO', 'ADMINISTRADOR']:
            flash('Rol inválido para registrarse', 'danger')
            return redirect(url_for('registrarse'))

        if not EMAIL_REGEX.match(correo):
            flash('Correo inválido.', 'danger'); return redirect(url_for('registrarse'))
        if not (5 <= len(correo) <= 25):
            flash('Correo debe tener 5–25 caracteres.', 'danger'); return redirect(url_for('registrarse'))
        if not PASSWORD_REGEX.match(contrasena) or correo.lower() in contrasena.lower():
            flash('Contraseña inválida (8–64, mayúsculas, minúsculas, dígitos, símbolos).', 'danger'); return redirect(url_for('registrarse'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM Usuarios WHERE correo=?", (correo,))
        if cur.fetchone():
            cur.close(); conn.close()
            flash('El correo ya está registrado.', 'danger'); return redirect(url_for('registrarse'))

        cur.execute("INSERT INTO Usuarios(correo, contrasena, rol) VALUES (?, ?, ?)",
                    (correo, contrasena, rol))
        conn.commit()
        cur.close()
        conn.close()

        flash('Registro exitoso. Inicia sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('registrarse.html')




















@app.route('/candidato/perfil')
def perfil_candidato():
    if 'usuario' not in session or session['usuario']['rol'] != 'CANDIDATO':
        return redirect(url_for('login'))

    id_asp = session['usuario']['id_aspirante']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Aspirantes WHERE id_aspirante = ?", (id_asp,))
    row = cursor.fetchone()

    candidato = {}
    if row:
        cols = [col[0].lower() for col in cursor.description]
        candidato = dict(zip(cols, row))

    cursor.close()
    conn.close()
    return render_template('candidato/perfil.html', candidato=candidato)

@app.route('/candidato/editar_perfil', methods=['GET', 'POST'])
def editar_perfil_candidato():
    if 'usuario' not in session or session['usuario']['rol'] != 'CANDIDATO':
        return redirect(url_for('login'))

    user = session['usuario']
    id_asp = user['id_aspirante']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Intentar recuperar el id_aspirante si existe
    cursor.execute("SELECT id_aspirante FROM Aspirantes WHERE id_usuario = ?", (user['id'],))
    row = cursor.fetchone()
    id_asp = row.id_aspirante if row else None

    cursor.execute("SELECT id_aspirante, foto_perfil, cv_pdf FROM Aspirantes WHERE id_usuario = ?", (user['id'],))
    aspirante_row = cursor.fetchone()

    if aspirante_row:
        id_asp = aspirante_row.id_aspirante
        foto_perfil_path = aspirante_row.foto_perfil
        cv_pdf_path = aspirante_row.cv_pdf
        existe = True
    else:
        id_asp = None
        foto_perfil_path = cv_pdf_path = None
        existe = False

    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '')
            apellido_paterno = request.form.get('apellido_paterno', '')
            apellido_materno = request.form.get('apellido_materno', '')
            telefono = request.form.get('telefono', '')
            estado_civil = request.form.get('estado_civil', '')
            sexo = request.form.get('sexo', '')
            fecha_nacimiento = request.form.get('fecha_nacimiento', '')
            nacionalidad = request.form.get('nacionalidad', '')
            rfc = request.form.get('rfc', '')
            direccion = request.form.get('direccion', '')
            disponibilidad_reubicacion = 1 if request.form.get('disponibilidad_reubicacion') else 0
            disponibilidad_viajar = 1 if request.form.get('disponibilidad_viajar') else 0
            licencia_conducir = 1 if request.form.get('licencia_conducir') else 0
            modalidad = request.form.get('modalidad', '')
            puesto_actual = request.form.get('puesto_actual', '')
            resumen = request.form.get('resumen', '')

        if id_asp:
            cursor.execute("SELECT 1 FROM Aspirantes WHERE id_aspirante = ?", (id_asp,))
            existe = cursor.fetchone()

            if existe:
                # Ya existe → hacer UPDATE
                cursor.execute("""
                    UPDATE Aspirantes SET nombre=?, telefono=?, resumen=? WHERE id_aspirante=?
                """, (nombre, telefono, resumen, id_asp))
            else:
                # No existe → hacer INSERT
                cursor.execute("""
                    INSERT INTO Aspirantes (id_usuario, nombre, telefono, resumen)
                    VALUES (?, ?, ?, ?)
                """, (user['id'], nombre, telefono, resumen))
                cursor.execute("SELECT SCOPE_IDENTITY()")
                nuevo_id = cursor.fetchone()[0]
                cursor.execute("UPDATE Usuarios SET id_aspirante=? WHERE id_usuario=?", (nuevo_id, user['id']))
                session['usuario']['id_aspirante'] = nuevo_id
        else:
            # Caso de seguridad extra: si no hay id_asp, igual se inserta
            cursor.execute("""
                INSERT INTO Aspirantes (id_usuario, nombre, telefono, resumen)
                VALUES (?, ?, ?, ?)
            """, (user['id'], nombre, telefono, resumen))
            cursor.execute("SELECT SCOPE_IDENTITY()")
            nuevo_id = cursor.fetchone()[0]
            cursor.execute("UPDATE Usuarios SET id_aspirante=? WHERE id_usuario=?", (nuevo_id, user['id']))
            session['usuario']['id_aspirante'] = nuevo_id

            conn.commit()
            flash('Perfil actualizado correctamente', 'success')
            return redirect(url_for('perfil_candidato'))

        except Exception as e:
            conn.rollback()
            flash(f'Error al actualizar perfil: {str(e)}', 'danger')
            app.logger.error(f'Error en editar_perfil_candidato: {str(e)}')

    candidato = {}
    if existe:
        cursor.execute("SELECT * FROM Aspirantes WHERE id_usuario = ?", (user['id'],))
        row = cursor.fetchone()
        if row:
            cols = [col[0].lower() for col in cursor.description]
            candidato = dict(zip(cols, row))

    cursor.close()
    conn.close()
    return render_template('candidato/editar_perfil.html', candidato=candidato)



@app.route('/candidato/vacantes')
def vacantes_candidato():
    if 'usuario' not in session or session['usuario']['rol'] != 'CANDIDATO':
        return redirect(url_for('login'))

    id_asp = session['usuario']['id_aspirante']
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT V.id_vacante, V.nombre_empresa, V.puesto, V.resumen, V.estado, V.cantidad_plazas,
               (
                   SELECT COUNT(*) 
                   FROM Postulaciones P 
                   WHERE P.id_vacante = V.id_vacante AND P.estado = 'aceptado'
               ) AS ocupadas,
               (
                   SELECT COUNT(*) 
                   FROM Postulaciones 
                   WHERE id_aspirante = ? AND id_vacante = V.id_vacante
               ) AS ya_postulado
        FROM Vacantes V
        WHERE estado = 'abierta'
    """, (id_asp,))
    
    rows = cursor.fetchall()
    cols = [col[0].lower() for col in cursor.description]
    vacantes = [dict(zip(cols, row)) for row in rows]
    
    cursor.close()
    conn.close()

    return render_template('candidato/vacantes.html', vacantes=vacantes)




@app.route('/candidato/postular/<int:id_vacante>', methods=['POST'])
def postular_vacante(id_vacante):
    if 'usuario' not in session or session['usuario']['rol'] != 'CANDIDATO':
        return redirect(url_for('login'))

    id_usuario = session['usuario']['id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener id_aspirante confiable desde BD
    cursor.execute("SELECT id_aspirante FROM Aspirantes WHERE id_usuario = ?", (id_usuario,))
    row = cursor.fetchone()

    if not row:
        flash('Debes completar tu perfil antes de postularte.', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('vacantes_candidato'))

    id_asp = row.id_aspirante

    try:
        # Validar si ya está postulando a esa vacante
        cursor.execute("""
            SELECT 1 FROM Postulaciones WHERE id_aspirante = ? AND id_vacante = ?
        """, (id_asp, id_vacante))
        if cursor.fetchone():
            flash('Ya te has postulado a esta vacante.', 'warning')
        else:
            cursor.execute("""
                INSERT INTO Postulaciones (id_aspirante, id_vacante, fecha_postulacion, estado)
                VALUES (?, ?, GETDATE(), 'pendiente')
            """, (id_asp, id_vacante))
            conn.commit()
            flash('Postulación realizada con éxito', 'success')
    except Exception as e:
        flash(f'Error al postular: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('vacantes_candidato'))

    return redirect(url_for('vacantes_candidato'))



@app.route('/candidato/postulaciones')
def postulaciones_candidato():
    if 'usuario' not in session or session['usuario']['rol'] != 'CANDIDATO':
        return redirect(url_for('login'))

    id_asp = session['usuario']['id_aspirante']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.puesto, p.fecha_postulacion, p.estado
        FROM Postulaciones p
        JOIN Vacantes v ON p.id_vacante = v.id_vacante
        WHERE p.id_aspirante = ?
    """, (id_asp,))
    rows = cursor.fetchall()
    postulaciones = [{'titulo': row[0], 'fechapostulacion': row[1], 'estado': row[2]} for row in rows]
    cursor.close()
    conn.close()

    return render_template('candidato/postulaciones.html', postulaciones=postulaciones)















































# --------------------------
# Rutas para Administrador
# --------------------------

@app.route('/admin/dashboard')
def dashboard_admin():
    if 'usuario' not in session or session['usuario']['rol'] != 'ADMINISTRADOR':

        return redirect(url_for('login'))
    return render_template('administrador/dashboard.html')


@app.route('/admin/candidatos')
def candidatos_admin():
    if 'usuario' not in session or session['usuario']['rol'] != 'ADMINISTRADOR':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT A.id_aspirante, A.nombre, A.telefono, U.correo
        FROM Aspirantes A
        JOIN Usuarios U ON A.id_usuario = U.id_usuario
    """)
    rows = cursor.fetchall()
    cols = [col[0].lower() for col in cursor.description]
    candidatos = [dict(zip(cols, row)) for row in rows]
    cursor.close()
    conn.close()

    return render_template('administrador/candidatos.html', candidatos=candidatos)


@app.route('/admin/vacantes')
def vacantes_admin():
    if 'usuario' not in session or session['usuario']['rol'] != 'ADMINISTRADOR':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_vacante, nombre_empresa, puesto, resumen, estado
        FROM Vacantes
    """)
    rows = cursor.fetchall()
    cols = [col[0].lower() for col in cursor.description]
    vacantes = [dict(zip(cols, row)) for row in rows]
    cursor.close()
    conn.close()

    return render_template('administrador/vacantes.html', vacantes=vacantes)


@app.route('/admin/vacantes/crear', methods=['GET', 'POST'])
def crear_vacante_admin():
    if 'usuario' not in session or session['usuario']['rol'] != 'ADMINISTRADOR':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Cargamos habilidades disponibles
    cursor.execute("SELECT id_habilidad, nombre FROM Habilidades")
    habilidades = [{'id_habilidad': row[0], 'nombre': row[1]} for row in cursor.fetchall()]

    if request.method == 'POST':
        # Campos del formulario
        empresa = request.form.get('nombre_empresa', '').strip()
        puesto = request.form.get('puesto', '').strip()
        grado = request.form.get('grado_estudios', '').strip()
        resumen = request.form.get('resumen', '').strip()
        estado = 'abierta'

        try:
            plazas = int(request.form.get('cantidad_plazas', '1'))
            if plazas < 1 or plazas > 100:
                raise ValueError
        except ValueError:
            flash('Cantidad de plazas inválida (1-100)', 'danger')
            return render_template('administrador/crear_vacante.html', habilidades=habilidades)

        # Validaciones adicionales
        if not (2 <= len(empresa) <= 100):
            flash('Nombre de empresa inválido', 'danger')
            return render_template('administrador/crear_vacante.html', habilidades=habilidades)

        if not (2 <= len(puesto) <= 100):
            flash('Puesto inválido', 'danger')
            return render_template('administrador/crear_vacante.html', habilidades=habilidades)

        if not (2 <= len(grado) <= 100):
            flash('Grado de estudios inválido', 'danger')
            return render_template('administrador/crear_vacante.html', habilidades=habilidades)

        # Insertamos la vacante y recuperamos ID generado
        cursor.execute("""
            INSERT INTO Vacantes (nombre_empresa, puesto, grado_estudios, resumen, cantidad_plazas, estado)
            OUTPUT INSERTED.id_vacante
            VALUES (?, ?, ?, ?, ?, ?)
        """, (empresa, puesto, grado, resumen, plazas, estado))
        id_vacante = cursor.fetchone()[0]

        # Habilidades seleccionadas
        habilidades_ids = request.form.getlist('habilidades')
        obligatorias_ids = set(request.form.getlist('obligatorias'))

        for id_hab in habilidades_ids:
            obligatorio = 1 if id_hab in obligatorias_ids else 0
            cursor.execute("""
                INSERT INTO Vacante_Habilidad (id_vacante, id_habilidad, obligatorio)
                VALUES (?, ?, ?)
            """, (id_vacante, id_hab, obligatorio))

        conn.commit()
        flash('Vacante creada con éxito', 'success')
        return redirect(url_for('vacantes_admin'))

    cursor.close()
    conn.close()
    return render_template('administrador/crear_vacante.html', habilidades=habilidades)


@app.route('/admin/vacantes/editar/<int:id_vacante>', methods=['GET', 'POST'])
def editar_vacante_admin(id_vacante):
    if 'usuario' not in session or session['usuario']['rol'] != 'ADMINISTRADOR':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        empresa = request.form['nombre_empresa']
        puesto = request.form['puesto']
        resumen = request.form['resumen']

        cursor.execute("""
            UPDATE Vacantes
            SET nombre_empresa=?, puesto=?, resumen=?
            WHERE id_vacante=?
        """, (empresa, puesto, resumen, id_vacante))
        conn.commit()
        flash('Vacante actualizada con éxito', 'success')
        return redirect(url_for('vacantes_admin'))

    cursor.execute("SELECT * FROM Vacantes WHERE id_vacante=?", (id_vacante,))
    vacante = cursor.fetchone()
    if not vacante:
        flash('Vacante no encontrada', 'danger')
        return redirect(url_for('vacantes_admin'))

    cols = [col[0].lower() for col in cursor.description]
    vacante = dict(zip(cols, vacante))
    cursor.close()
    conn.close()

    return render_template('administrador/editar_vacante.html', vacante=vacante)


@app.route('/admin/vacantes/eliminar/<int:id_vacante>', methods=['POST'])
def eliminar_vacante_admin(id_vacante):
    if 'usuario' not in session or session['usuario']['rol'] != 'ADMINISTRADOR':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Vacantes WHERE id_vacante = ?", (id_vacante,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Vacante eliminada correctamente', 'success')
    return redirect(url_for('vacantes_admin'))


@app.route('/admin/postulaciones')
def postulaciones_admin():
    if 'usuario' not in session or session['usuario']['rol'] != 'ADMINISTRADOR':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT P.id_postulacion, A.nombre, V.puesto, P.fecha_postulacion, P.estado
        FROM Postulaciones P
        JOIN Aspirantes A ON P.id_aspirante = A.id_aspirante
        JOIN Vacantes V ON P.id_vacante = V.id_vacante
    """)
    rows = cursor.fetchall()
    cols = [col[0].lower() for col in cursor.description]
    postulaciones = [dict(zip(cols, row)) for row in rows]
    cursor.close()  
    conn.close()

    return render_template('administrador/postulaciones.html', postulaciones=postulaciones)
