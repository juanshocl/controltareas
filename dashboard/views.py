import json, requests, jwt
from controltareas.settings import API
from django.http.request import HttpHeaders
from django.shortcuts import render, redirect
from django.http import HttpResponse
from requests.api import delete, head, request
from login.views import authenticated, decodered
from datetime import datetime
from random import randint
from messagesMail.tasks import sendEmailTask

def dashboard(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        rol = data['role']
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        dataAPI = requests.get(API+'usuario/', headers=headers).json()
        allTask = requests.get(API+'tarea', headers=headers).json()
        
        taskeOnExecute = list(e for e in allTask['data'] if e['fkEstadoTarea']  ==  2 or e['fkEstadoTarea']  ==  3 )
        taskFinished = list(e for e in allTask['data'] if e['fkEstadoTarea']  == 5  )
        taskOverDue = list(e for e in allTask['data'] if e['fkEstadoTarea']  == 6  )
        
        if int(rol) == 1:
            context = {
                    'menu' : 'dashboard',
                    'email' : data['email'],
                    'name': data['unique_name'],
                    'role': int(data['role']),
                    'login' : datetime.fromtimestamp(data['nbf']),
                    'usuarios': dataAPI['data'],
                    'allTaskOnExecute': len(taskeOnExecute),
                    'allTask': len(allTask['data']),
                    'percentOnExecute': int((len(taskeOnExecute)*100)/len(allTask['data'])),
                    'percentFinished': int((len(taskFinished)*100)/len(allTask['data'])),
                    'percentOverDue': int((len(taskOverDue)*100)/len(allTask['data'])),
                    'taskFinished': len(taskFinished), 
                    'taskOverDue': len(taskOverDue),
                    'task': allTask['data'],
            }
        
        elif int(rol) == 2:
            context = {
                    'menu' : 'dashboardFuncionario',
                    'email' : data['email'],
                    'name': data['unique_name'],
                    'role': int(data['role']),
                    'login' : datetime.fromtimestamp(data['nbf']),
                    'usuarios': dataAPI['data'], 
            }
        else:
            context = {
                    'menu' : 'dashboardFuncionario',
                    'email' : data['email'],
                    'name': data['unique_name'],
                    'role': int(data['role']),
                    'login' : datetime.fromtimestamp(data['nbf']),
                    'usuarios': dataAPI['data'], 
            }
            
        return render(request,'home/home.html',{'datos': context})
    
    else:
        return redirect('login')

def tasklist(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        tareas = requests.get(API+'tarea/', headers=headers ).json()
        usuarios = requests.get(API+'usuario/', headers=headers).json()
        #se edita el diccionario agregando porcentaje de avance de la tarea como un diccionario nuevo
        
        #Se utiliza para obtener los la unidad interna del usuario
        usuario = requests.get(API+'usuario/oneUser/'+str(data['nameid']), headers=headers).json()
        unidadInterna = requests.get(API+'unidadInterna/oneUnidadInterna/'+str(usuario['data'][0]['idUnidadInternaUsuario']) , headers=headers).json()
        
        unidadesInternas = requests.get(API+'unidadInterna/', headers=headers).json()
        
        unidadPorEmpresa = list(e for e in unidadesInternas['data'] if e['fkRutEmpresa']  == unidadInterna['data'][0]['fkRutEmpresa'])
        
        semaforo = 0
        
        
        
        tarea={}
        tarea['data']= []
        
        asignado = []
        for a in usuarios['data']:
            for b in unidadPorEmpresa:
                if a['idUnidadInternaUsuario'] == b['idUnidadInterna']:
                    asignado.append(a)
    
        for datos in tareas['data']:
            for us in asignado:
                if datos['fkRutUsuario'] == us['rutUsuario']:
                    dias = int((datetime.strptime(datos['fechaPlazo'] , '%Y-%m-%dT%H:%M:%S') - datetime.now()).days)
                    if dias > 7:
                        semaforo = 1
                    elif dias < 7 and dias > 0 : 
                        semaforo = 2
                    elif dias < 0:
                        semaforo = 3
                        
                    tarea['data'].append({
                    'idTarea': datos['idTarea'],
                    'nombreTarea': datos['nombreTarea'] ,
                    'descripcionTarea': datos['descripcionTarea'] ,
                    'fechaPlazo': datos['fechaPlazo'] ,
                    'fkRutUsuario': datos['fkRutUsuario'] ,
                    'fkEstadoTarea': datos['fkEstadoTarea'] ,
                    'fkPrioridadTarea': datos['fkPrioridadTarea'] ,
                    'percent': datos['porcentajeAvance'],
                    'semaforo':  semaforo,
                    }
                    )
        
        context = {
            'menu' : 'tableTask',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            'tk': tarea['data'],
            'usuarios': usuarios['data']
        }
        return render(request, 'task/tasklist.html',{'datos': context})
    else: 
        return redirect('login')
    
def taskdelete(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        deleted = requests.delete(API+'tarea/delete/'+str(id), headers=headers)
        
        print(deleted.status_code)
        if deleted.ok:
            message  = "Eliminado correctamente"
        else:
            message = "Ocurrio un error en el proceso, favor intente nuevamente"
        
        return redirect('tasklist')
    else: 
        return redirect('login')


def taskedit(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        usuarios = requests.get(API+'usuario/', headers=headers).json()
        prioridad = requests.get(API+'prioridadTarea', headers=headers).json()
        estado = requests.get(API+'estadoTarea', headers=headers).json()
        asignadoa = requests.get(API+'usuario', headers=headers).json()
        justificacion = requests.get(API+'justificacionTarea/', headers=headers).json()
        unaTarea = requests.get(API+'tarea/oneTask/'+str(id), headers=headers).json()

        
        creado = list(e for e in usuarios['data'] if e['rutUsuario']  == unaTarea['data'][0]['creadaPor'])

        
        
        context = {
        'menu' : 'taskedit',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'tareas' : unaTarea['data'][0],
        'usuarios': usuarios['data'],
        'prioridad': prioridad['data'],
        'estado': estado['data'],
        'asignadoa': asignadoa['data'],
        'creadopor':creado[0] ,
        'justificacion': justificacion['data'],
        }
        return render(request, 'task/task.html',{'datos': context})
    else:
        return redirect('login')


def teamwork(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        rol = data['role']
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }
        dataAPI = requests.get(API+'usuario/', headers=headers).json()
        roles = requests.get(API+'rol/', headers=headers).json()
        oneUser = requests.get(API+'usuario/oneUser/'+str(data['nameid']), headers=headers).json()
        unidadesInternas = requests.get(API+'unidadInterna/', headers=headers).json()
        unidadInterna = requests.get(API+'unidadInterna/oneUnidadInterna/'+str(oneUser['data'][0]['idUnidadInternaUsuario']) , headers=headers).json()
        unidad=[]
        
        for e in unidadesInternas['data']:
            if e['fkRutEmpresa'] == unidadInterna['data'][0]['fkRutEmpresa']:
                unidad.append(
                    e['idUnidadInterna']
                )

                
        
        if int(rol) == 1:

            usuario={}
            usuario['data']= []
            for datos in dataAPI['data']:
                if datos['idUnidadInternaUsuario'] in unidad:
                    usuario['data'].append({
                        'rutUsuario': datos['rutUsuario'],
                        'nombreUsuario': datos['nombreUsuario'] ,
                        'segundoNombre': datos['segundoNombre'] ,
                        'apellidoUsuario': datos['apellidoUsuario'] ,
                        'segundoApellido': datos['segundoApellido'] ,
                        'numTelefono': datos['numTelefono'] ,
                        'correoElectronico': datos['correoElectronico'] ,
                        'idRolUsuario': list(e for e in roles['data'] if e['rolId']  == datos['idRolUsuario'])[0]['nombreRol'],
                        'idUnidadInternaUsuario':list(e for e in unidadesInternas['data'] if e['idUnidadInterna']  == datos['idUnidadInternaUsuario'])[0]['nombreUnidad'],
                    }
                    )

        elif int(rol) == 2:

            usuario={}
            usuario['data']= []
            for datos in dataAPI['data']:
                if datos['idUnidadInternaUsuario'] in unidad:
                    usuario['data'].append({
                        'rutUsuario': datos['rutUsuario'],
                        'nombreUsuario': datos['nombreUsuario'] ,
                        'segundoNombre': datos['segundoNombre'] ,
                        'apellidoUsuario': datos['apellidoUsuario'] ,
                        'segundoApellido': datos['segundoApellido'] ,
                        'numTelefono': datos['numTelefono'] ,
                        'correoElectronico': datos['correoElectronico'] ,
                        'idRolUsuario': list(e for e in roles['data'] if e['rolId']  == datos['idRolUsuario'])[0]['nombreRol'],
                        'idUnidadInternaUsuario':list(e for e in unidadesInternas['data'] if e['idUnidadInterna']  == datos['idUnidadInternaUsuario'])[0]['nombreUnidad'],
                    }
                    )
                    
        context = {
            'menu' : 'teamwork',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            'teams': usuario['data'],

        }

        return render(request,'teamwork/teamwork.html',{'datos': context})
    else: 
        return redirect('login')

def workload(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        user = requests.get(API+'usuario/oneUser/'+str(id), headers=headers).json()
        tareas = requests.get(API+'tarea/', headers=headers).json()
        unidadinterna = requests.get(API+'unidadInterna/', headers=headers).json()
        roles = requests.get(API+'rol/', headers=headers).json()
        unidadesInternas = requests.get(API+'unidadInterna/', headers=headers).json()
        usuarios = requests.get(API+'usuario/', headers=headers).json()
        
        
        unidadInterna = requests.get(API+'unidadInterna/oneUnidadInterna/'+str(user['data'][0]['idUnidadInternaUsuario']) , headers=headers).json()
        
        unidad=[]

        for e in unidadesInternas['data']:
            if e['fkRutEmpresa'] == unidadInterna['data'][0]['fkRutEmpresa']:
                unidad.append(
                    e['idUnidadInterna']
                )
        
        
        t = []
        for e in usuarios['data']:
            if e['idUnidadInternaUsuario'] in unidad:
                t.append(
                    e['rutUsuario']
                )
        
        tempresa = list(e for e in tareas['data'] if e['fkRutUsuario'] in t)
        
        u = user['data'][0]
        
        usuario={}
        usuario['data']= []
        usuario['data'].append({
            'rutUsuario': u['rutUsuario'],
            'nombreUsuario': u['nombreUsuario'] ,
            'segundoNombre': u['segundoNombre'] ,
            'apellidoUsuario': u['apellidoUsuario'] ,
            'segundoApellido': u['segundoApellido'] ,
            'numTelefono': u['numTelefono'] ,
            'correoElectronico': u['correoElectronico'] ,
            'idRolUsuario': list(e for e in roles['data'] if e['rolId']  == u['idRolUsuario'])[0]['nombreRol'],
            'idUnidadInternaUsuario':list(e for e in unidadinterna['data'] if e['idUnidadInterna']  == u['idUnidadInternaUsuario'])[0]['nombreUnidad'],
            }
            )
        
        ontime = len(list(e for e in tareas['data'] if datetime.strptime(e['fechaPlazo'], '%Y-%m-%dT%H:%M:%S') >= datetime.now() and e['fkRutUsuario']  == user['data'][0]['rutUsuario'] and e['porcentajeAvance'] <100 ))
        atrasadas = len(list(e for e in tareas['data'] if datetime.strptime(e['fechaPlazo'], '%Y-%m-%dT%H:%M:%S') < datetime.now() and e['fkRutUsuario']  == user['data'][0]['rutUsuario'] and e['porcentajeAvance'] <100  ))
        asignadas = list(e for e in tareas['data'] if e['fkRutUsuario']  == user['data'][0]['rutUsuario'] and e['porcentajeAvance'] <100)
        
        context = {
            'menu' : 'workload',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login': datetime.fromtimestamp(data['nbf']),
            'tareas': asignadas,
            'user': usuario['data'][0],
            'asignadas': len(asignadas),             
            'atrasadas': atrasadas,
            'atiempo': ontime,
            'pAtrasadas': float((100*int(atrasadas))/int(len(asignadas))),
            'pTAsignadas': float((100*int(len(asignadas)))/int(len(tempresa))),
            'pOntime': float((100*int(ontime))/int(len(asignadas))) ,
                
        }
        return render(request, 'teamwork/workload.html',{'datos': context})
    else: 
        return redirect('login')

#Lista de detalle de las tareas creadas
def taskdetails(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        tareas = requests.get(API+'tarea/', headers=headers ).json()
        usuarios = requests.get(API+'usuario/', headers=headers).json()
        justificacion = requests.get(API+'justificacionTarea', headers=headers).json()
        tareasDetalle = list(e for e in tareas['data'] if e['idTarea']  == int(id))[0]
        
        context = {
            'menu' : 'taskdetails',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            'tareas': tareasDetalle,
            'usuarios': usuarios['data'],
            #'actividades' : list(e for e in justificacion['data'] if e['fkTareaId']  == tareasDetalle['idTarea']),
        }
        return render(request, 'task/taskdetails.html',{'datos': context})
    else: 
        return redirect('login')
    
#Creacion de tareas renderizado del template
def tasknew(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        usuarios = requests.get(API+'usuario/', headers=headers).json()
        prioridad = requests.get(API+'prioridadTarea', headers=headers).json()
        estado = requests.get(API+'estadoTarea', headers=headers).json()
        creadopor = requests.get(API+'usuario', headers=headers).json()
                
        context = {
            'menu' : 'tasknew',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            'usuarios': usuarios['data'],
            'prioridad': prioridad['data'],
            'estado': estado['data'],
            'creadopor': creadopor['data'],
        }
        return render(request, 'task/task.html',{'datos': context})
    else: 
        return redirect('login')
    
    
#Metodo que modifica estado de tarea a completada
def taskcomplete(request,idTask):
    if authenticated(request):
        token = request.COOKIES.get('validate')

        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        tarea = requests.get(API+'tarea/oneTask/'+str(idTask), headers=headers).json()
        userCreate = requests.get(API+'usuario/oneUser/'+str(tarea['data'][0]['creadaPor']), headers=headers).json()
        
        userAssign = requests.get(API+'usuario/oneUser/'+str(tarea['data'][0]['fkRutUsuario']), headers=headers).json()

        finishedTask = requests.put(API+'tarea/finishedTask/'+str(idTask), headers=headers)
        
        destinatarios = []
        destinatarios.append(userCreate['data'][0]['correoElectronico'])
        destinatarios.append(userAssign['data'][0]['correoElectronico'])
        
        if request.POST.get('checkboxProblema') or request.POST.get('inputProblema'):
            #Se crea el cuerpo del mensaje para el reporte problema 
            payload = json.dumps(
                {
                'ReporteProblema': request.POST.get('inputProblema'),
                })
            problema = requests.put(API+'tarea/reportProblem/'+str(idTask), headers=headers, data = payload)
            data = {
                'evento': 'Reporte Problema',
                'user': userCreate['data'][0]['nombreUsuario']+' '+ userCreate['data'][0]['apellidoUsuario'],
                'email': userCreate['data'][0]['correoElectronico'],
                'tarea': tarea['data'][0],
                'problema': request.POST.get('inputProblema'),
                
            }

            
        else:            
            data = {
                'evento': 'Finalización de tarea',
                'multi' : True,
                'email': destinatarios,
                'tarea': tarea['data'][0],
                }
        
        if 'taskfuncionario' in request.META['HTTP_REFERER']:
            sendEmailTask.delay(data) #Notifica al usuario que tiene asignada la tarea
            return redirect('taskfuncionario')
        elif 'tasklist' in request.META['HTTP_REFERER'] and finishedTask.ok:
            #Aqui
            sendEmailTask.delay(data) #Notifica al usuario que tiene asignada la tarea
            return redirect('tasklist')
        else:
            return redirect('dashboard')
    else: 
        return redirect('login')

#modificado por Alejandro
def updatetask(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        user = requests.get(API+'usuario/', headers=headers).json()
        prioridad = requests.get(API+'prioridadTarea', headers=headers).json()

        payload = json.dumps(
        {
            'nombreTarea':request.POST.get('nombretarea'),
            'descripcionTarea': request.POST.get('descripciontarea'),
            # 'fechaPlazo': request.POST.get('fechaplazo'),
            'porcentajeAvance': int(request.POST.get('porcentaje')),
            # 'creadaPor': request.POST.get('creadoporRut'),  #cre
            'fkRutUsuario' : request.POST.get('asignadoa'),
            'fkEstadoTarea': int(request.POST.get('estadotarea')),
            'fkPrioridadTarea' : int(request.POST.get('prioridadtarea')),
        })
        update = requests.put(API+'tarea/update/'+str(id), headers=headers, data = payload)
        if update.ok: 
            if int(request.POST.get('estadotarea'))== 2:
                usuario = list(e for e in user['data'] if e['rutUsuario']  == request.POST.get('asignadoa'))[0]
                tarea = requests.get(API+'tarea/oneTask/'+str(id), headers=headers).json()
                data = {
                    'evento': 'Actualizacion de tarea', 
                    'email': usuario['correoElectronico'],
                    'user': usuario['nombreUsuario']+' '+ usuario['apellidoUsuario'],
                    'tarea': tarea['data'][0],
                    # 'prioridad': list(e for e in prioridad['data'] if e['idPrioridad']  == int(request.POST.get('prioridadtarea')) )[0]['descripcion'],
                }
                sendEmailTask.delay(data) #Notifica al usuario que tiene asignada la tarea

            return redirect('tasklist')
        else:
            return redirect('dashboard') #envia al dashboard si da error
    else:
        return redirect('login')

#Salvar datos de la nueva tarea
#modificado por Alejandro
def savenewtask(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        user = requests.get(API+'usuario/', headers=headers).json()
        data = decodered(token)

        # print(asignadoa)
        payload = json.dumps({
            'nombreTarea':request.POST.get('nombretarea'),#
            'descripcionTarea': request.POST.get('descripciontarea'),
            'fechaPlazo': request.POST.get('fechaplazo'),
            'porcentajeAvance':0,
            'fechaCreacion': request.POST.get('fechaplazo'),
            'creadaPor': data['nameid'],
            'fkRutUsuario': data['nameid'],
            'fkEstadoTarea' : int(1),
            'fkPrioridadTarea' : int(request.POST.get('prioridadtarea')),

        })
        r = requests.post(API+'tarea/add', headers=headers, data=payload)
        print(r.content)
        if r.ok:
            print('Tarea creado correctamente')
            print(r.content)
        else:
            print('Error')
            print(r.status_code)


        return redirect('tasklist')
    else: 
        return redirect('login')

#Creacion de nuevos usuarios
def createnewuser(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        
        payload = json.dumps({
            'RutUsuario': request.POST.get('rut'),
            'NombreUsuario': request.POST.get('name'),
            'SegundoNombre': request.POST.get('secondName'),
            'ApellidoUsuario': request.POST.get('secondName'),
            'SegundoApellido': request.POST.get('secondlastName'),
            'CorreoElectronico': request.POST.get('email'),
            'NumTelefono': int(request.POST.get('phoneNumber')),
            'Password': request.POST.get('password'),
            'IdRolUsuario': int(request.POST.get('role')),
            'idUnidadInternaUsuario': int(request.POST.get('unidadInterna')),
            
        })

        r = requests.post(API+'usuario/add', headers=headers, data=payload)

        if r.ok:
            print('Usuario creado correctamente')
            return redirect('listusers')
            
        else:
            print('Error')
            #Aca podria ir un mensaje o no?
            context = {
            'menu' : 'newuser',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            }
            return render(request, 'users/newuser.html',{'datos': context})
            
            

    else: 
        return redirect('login')
    
#Renderizado de template de creacion de usuarios 
def newuser(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        rol = requests.get(API+'rol/', headers=headers).json()
        unidades = requests.get(API+'unidadInterna/', headers=headers).json()
        context = {
            'menu' : 'newuser',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            'unidad': unidades['data'],
            'rol': rol['data'],
        }
        return render(request, 'users/newuser.html',{'datos': context})
    else: 
        return redirect('login')

#Listo los datos del usuario existente
def viewusers(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        user = requests.get(API+'usuario/oneUser/'+str(id), headers=headers).json()
        tareas = requests.get(API+'tarea/', headers=headers).json()


        context = {
            'menu' : 'viewusers',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login': datetime.fromtimestamp(data['nbf']),
            'tareas': list(e for e in tareas['data'] if e['fkRutUsuario']  == user['data'][0]['rutUsuario']),
            'user': user['data'][0],
        }
        return render(request, 'users/userdetails.html',{'datos': context})
    else: 
        return redirect('login')
    
#Listado de usuarios en perfil de administrador
def listusers(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        usuarios = requests.get(API+'usuario/', headers=headers).json()
        roles = requests.get(API+'rol/', headers=headers).json()
        unidadesInternas = requests.get(API+'unidadInterna/', headers=headers).json()
        
        oneUser = requests.get(API+'usuario/oneUser/'+str(data['nameid']), headers=headers).json()
        unidadInterna = requests.get(API+'unidadInterna/oneUnidadInterna/'+str(oneUser['data'][0]['idUnidadInternaUsuario']) , headers=headers).json()
        
        unidad=[]
        
        for e in unidadesInternas['data']:
            if e['fkRutEmpresa'] == unidadInterna['data'][0]['fkRutEmpresa']:
                unidad.append(
                    e['idUnidadInterna']
                )
            
        usuario={}
        usuario['data']= []
        for datos in usuarios['data']:
            if datos['idUnidadInternaUsuario'] in unidad:
                usuario['data'].append({
                    'rutUsuario': datos['rutUsuario'],
                    'nombreUsuario': datos['nombreUsuario'] ,
                    'segundoNombre': datos['segundoNombre'] ,
                    'apellidoUsuario': datos['apellidoUsuario'] ,
                    'segundoApellido': datos['segundoApellido'] ,
                    'numTelefono': datos['numTelefono'] ,
                    'correoElectronico': datos['correoElectronico'] ,
                    'idRolUsuario': list(e for e in roles['data'] if e['rolId']  == datos['idRolUsuario'])[0]['nombreRol'],
                    'idUnidadInternaUsuario':list(e for e in unidadesInternas['data'] if e['idUnidadInterna']  == datos['idUnidadInternaUsuario'])[0]['nombreUnidad'],
                    }
                    )
        
        
        context = {
        'menu' : 'listusers',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'usuarios': usuario['data'],
        }
        return render(request, 'users/userlist.html',{'datos': context})
    else: 
        return redirect('login')

def editusers(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        user = requests.get(API+'usuario/oneUser/'+str(id), headers=headers).json()
        rol = requests.get(API+'rol/', headers=headers).json()
        unidades = requests.get(API+'unidadInterna/', headers=headers).json()
        
        context = {
        'menu' : 'editusers',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'user': user['data'][0],
        'unidad': unidades['data'],
        'rol': rol['data'],
        }
        return render(request, 'users/newuser.html',{'datos': context})
    else:
        return redirect('login')

def deleteusers(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        payload = json.dumps({'IdUnidadInterna': id})
        headers={'Accept-Encoding': 'UTF-8','Content-Type':'application/json','Accept': '*/*' ,'Authorization': 'Bearer '+token}
        deleted = requests.delete(API+'usuario/delete/'+str(id), headers=headers)
        if deleted.ok:
            message  = "Eliminado correctamente"
        else:
            message = "Ocurrio un error en el proceso, favor intente nuevamente"
        
        return redirect('listusers')
    else:
        return redirect('login')


def updateusers(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        payload = json.dumps(
            {
            'rutUsuario': request.POST.get('rut'),
            'nombreUsuario': request.POST.get('name'),
            'segundoNombre': request.POST.get('secondName'),
            'apellidoUsuario': request.POST.get('lastName'),
            'segundoApellido': request.POST.get('secondlastName'),
            'correoElectronico': request.POST.get('email'),
            'numTelefono': int(request.POST.get('phoneNumber')),
            'idRolUsuario': int(request.POST.get('role')),
            'idUnidadInternaUsuario': int(request.POST.get('unidadInterna'))
        }
            )
        update = requests.put(API+'usuario/update/'+str(id), headers=headers, data = payload)
        if update.ok:
            return redirect('listusers')
        else:
            return redirect('dashboard') #envia al dashboard si da error
    else:
        return redirect('login')
    

def createnewunits(request):
    token = request.COOKIES.get('validate')
    headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
    payload = json.dumps({
        'NombreUnidad': request.POST.get('nombreunit'),
        'fkRutEmpresa': request.POST.get('fkRutEmpresa'),
        'DescripcionUnidad': request.POST.get('descriptunit') 
    })
    r = requests.post(API+'unidadInterna/add/', headers=headers, data=payload)
    if r.ok:

        return redirect('listunits')
    else:
        return redirect('dashboard')
    

def newunits(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        empresas = requests.get(API+'business', headers=headers).json()
        context = {
        'menu' : 'newunits',
        'email' : data['email'],
        'name': data['unique_name'],
        'empresas': empresas['data'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        }
        return render(request, 'units/units.html',{'datos': context})
    else:
        return redirect('login')

def viewunits(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        units = requests.get(API+'unidadInterna/', headers=headers).json()
        for i in units['data']:
            if i['idUnidadInterna'] == id:
                unidad = i
                
        context = {
        'menu' : 'viewunits',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'unidad': unidad,
        }
        return render(request, 'units/units.html',{'datos': context})
    else:
        return redirect('login')
    
def editunits(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        units = requests.get(API+'unidadInterna/', headers=headers).json()
        empresa = requests.get(API+'business', headers=headers).json()
        for i in units['data']:
            if i['idUnidadInterna'] == id:
                unidad = i

        for x in empresa['data']:
            if x['rutEmpresa'] == unidad['fkRutEmpresa']:
                empresa  = x
                
        context = {
        'menu' : 'editunits',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'empresas': empresa,
        'login' : datetime.fromtimestamp(data['nbf']),
        'unidad': unidad,
        }
        return render(request, 'units/units.html',{'datos': context})
    else:
        return redirect('login')

def updateunits(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        payload = json.dumps(
            {
        'NombreUnidad': request.POST.get('nombreunit'),
        'DescripcionUnidad': request.POST.get('descriptunit') 
        }
            )
        update = requests.put(API+'unidadInterna/update/'+str(id), headers=headers, data = payload)
        if update.ok:
            return redirect('listunits')
        else:
            return redirect('dashboard') #envia al dashboard si da error
    else:
        return redirect('login')
    
def deleteunits(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        payload = json.dumps({'IdUnidadInterna': id})
        headers={'Accept-Encoding': 'UTF-8','Content-Type':'application/json','Accept': '*/*' ,'Authorization': 'Bearer '+token}
        deleted = requests.delete(API+'unidadInterna/delete/'+str(id), headers=headers)
        

        if deleted.ok:
            message  = "Eliminado correctamente"
        else:
            message = "Ocurrio un error en el proceso, favor intente nuevamente"
        
        return redirect('listunits')
    else:
        return redirect('login')

def listunits(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8','Content-Type': 'application/json','Accept': '*/*' ,'Authorization': 'Bearer '+token}
        units = requests.get(API+'unidadInterna/', headers=headers).json()
        user = requests.get(API+'usuario/oneUser/'+data['nameid'], headers=headers).json()
        unidadInterna = requests.get(API+'unidadInterna/oneUnidadInterna/'+str(user['data'][0]['idUnidadInternaUsuario']) , headers=headers).json()
                
        unidad=[]

        for e in units['data']:
            if e['fkRutEmpresa'] == unidadInterna['data'][0]['fkRutEmpresa']:
                unidad.append(
                    e['idUnidadInterna']
                )
                
        context = {
        'menu' : 'listunits',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'unidades': list(e for e in units['data'] if e['idUnidadInterna'] in unidad),
        }
        return render(request, 'units/unitslist.html',{'datos': context})
    else: 
        return redirect('login')


def newrole(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        
        context = {
        'menu' : 'newrole',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        }
        return render(request, 'role/role.html',{'datos': context})
    else:
        return redirect('login')

def viewrole(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        rollist = requests.get(API+'rol/', headers=headers).json()
        print(rollist)
        for i in rollist['data']:
            if i['rolId'] == id:
                rol = i
        print(rol) 
        context = {
        'menu' : 'viewrole',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'rollist': rol,
        }
        return render(request, 'role/role.html',{'datos': context})
    else:
        return redirect('login')


def editrole(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        rollist = requests.get(API+'rol/', headers=headers).json()
        print(rollist)
        for i in rollist['data']:
            if i['rolId'] == id:
                rol = i
        print(rol) 
                
        context = {
        'menu' : 'editrole',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'rollist': rol,
        }
        return render(request, 'role/role.html',{'datos': context})
    else:
        return redirect('login')

def updaterole(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        headers={'Content-Type':'application/json', 'Authorization': 'Bearer '+token}
        payload = json.dumps(
            {
        'nombreRol': request.POST.get('nombrerol'),
        'DescripcionRol': request.POST.get('descriptrole') 
        }
            )
        update = requests.put(API+'rol/update/'+str(id), headers=headers, data = payload)
        if update.ok:
            return redirect('listrole')
        else:
            return redirect('dashboard') #envia al dashboard si da error
    else:
        return redirect('login')
    
def deleterole(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        headers={'Accept-Encoding': 'UTF-8','Content-Type':'application/json','Accept': '*/*' ,'Authorization': 'Bearer '+token}
        deleted = requests.delete(API+'rol/delete/'+str(id), headers=headers)

        if deleted.ok:
            message  = "Eliminado correctamente"
        else:
            message = "Ocurrio un error en el proceso, favor intente nuevamente"
        
        return redirect('listrole')
    else:
        return redirect('login')

def listrole(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers={'Accept-Encoding': 'UTF-8','Content-Type':'application/json','Accept': '*/*' ,'Authorization': 'Bearer '+token}
        roles = requests.get(API+'rol/', headers=headers).json()
        context = {
        'menu' : 'listrole',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'roles': roles['data'],
        }
        return render(request, 'role/rolelist.html',{'datos': context})
    else: 
        return redirect('login')

def createnewrole(request):
    token = request.COOKIES.get('validate')
    headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
    payload = json.dumps({
        'nombreRol': request.POST.get('nombrerol'),
        'DescripcionRol': request.POST.get('descriptrole') 
    })
    r = requests.post(API+'rol/add/', headers=headers, data=payload)
    print(r.content)
    if r.ok:

        return redirect('listrole')
    else:
        return redirect('dashboard')
    



def workflowlist(request):
    context = {
    'menu' : 'workflowlist',
    'email' : 'juan@micorreo.cl',
    'name': 'juan muñoz',
    'role': 3,
    'login' : datetime.now(),
    }
    return render(request, 'workflow/workflowlist.html',{'datos': context})

def workflownew(request):
    context = {
    'menu' : 'workflownew',
    'email' : 'juan@micorreo.cl',
    'name': 'juan muñoz',
    'role': 1,
    'login' : datetime.now(),
    }
    return render(request, 'workflow/workflownew.html',{'datos': context})

def workflowview(request):
    context = {
    'menu' : 'workflowview',
    'email' : 'juan@micorreo.cl',
    'name': 'juan muñoz',
    'role': 1,
    'login' : datetime.now(),
    }
    return render(request, 'workflow/workflowview.html',{'datos': context})

def workflowhistory(request):
    context = {
    'menu' : 'workflowhistory',
    'email' : 'juan@micorreo.cl',
    'name': 'juan muñoz',
    'role': 3,
    'login' : datetime.now(),
    }
    return render(request, 'workflow/workflowhistory.html',{'datos': context})


#Metodos para perfil funcionario

def taskfuncionario(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        tareas = requests.get(API+'tarea/', headers=headers ).json()
        usuarios = requests.get(API+'usuario/', headers=headers).json()
        tareasf = list(e for e in tareas['data'] if e['fkRutUsuario']  == data['nameid'] and e['fkEstadoTarea'] == 2 )
        tareasf2 = list(e for e in tareas['data'] if e['fkRutUsuario']  == data['nameid'])
        semaforo = 0
        #se edita el diccionario agregando porcentaje de avance de la tarea como un diccionario nuevo
        tarea={}
        tarea['data']= []
        for datos in tareasf:
            dias = int((datetime.strptime(datos['fechaPlazo'] , '%Y-%m-%dT%H:%M:%S') - datetime.now()).days)
            if dias > 7:
                semaforo = 1
            elif dias < 7 and dias > 0 : 
                semaforo = 2
            elif dias < 0:
                semaforo = 3
            tarea['data'].append({
            'idTarea': datos['idTarea'],
            'nombreTarea': datos['nombreTarea'] ,
            'descripcionTarea': datos['descripcionTarea'] ,
            'fechaPlazo': datos['fechaPlazo'] ,
            'fkRutUsuario': datos['fkRutUsuario'] ,
            'fkEstadoTarea': datos['fkEstadoTarea'] ,
            'fkPrioridadTarea': datos['fkPrioridadTarea'] ,
            'percent': datos['porcentajeAvance'],
            'semaforo': semaforo,
            }
            )

        tarea2={}
        tarea2['data']= []
        for datos in tareasf2:
            if datos['fkEstadoTarea'] == 3 or datos['fkEstadoTarea'] == 6 or datos['fkEstadoTarea'] == 5:
                dias = int((datetime.strptime(datos['fechaPlazo'] , '%Y-%m-%dT%H:%M:%S') - datetime.now()).days)
                if dias > 7:
                    semaforo = 1
                elif dias < 7 and dias > 0 : 
                    semaforo = 2
                elif dias < 0:
                    semaforo = 3
                tarea2['data'].append({
                'idTarea': datos['idTarea'],
                'nombreTarea': datos['nombreTarea'] ,
                'descripcionTarea': datos['descripcionTarea'] ,
                'fechaPlazo': datos['fechaPlazo'],
                'fkRutUsuario': datos['fkRutUsuario'] ,
                'fkEstadoTarea': datos['fkEstadoTarea'] ,
                'fkPrioridadTarea': datos['fkPrioridadTarea'] ,
                'percent': datos['porcentajeAvance'],
                'semaforo': semaforo,
                
                }
                )
        

        context = {
        'menu' : 'taskfuncionario',
        'email' : data['email'],
        'name': data['unique_name'],
        'role': int(data['role']),
        'login' : datetime.fromtimestamp(data['nbf']),
        'tk': tarea['data'],
        'tk2': tarea2['data'],
        'usuarios': usuarios['data']
        }
        return render(request, 'task/tasklist.html',{'datos': context})
    else: 
        return redirect('login')

def messagelist(request):
    context = {
    'menu' : 'messagelist',
    'email' : 'juan@micorreo.cl',
    'name': 'juan muñoz',
    'role': 2,
    'login' : datetime.now(),
    }
    return render(request, 'messages/messagelist.html',{'datos': context})

def messagereaded(request):
    context = {
    'menu' : 'messagereaded',
    'email' : 'juan@micorreo.cl',
    'name': 'juan muñoz',
    'role': 2,
    'login' : datetime.now(),
    }
    return render(request, 'messages/messagereaded.html',{'datos': context})

def messageresponded(request):
    context = {
    'menu' : 'messageresponded',
    'email' : 'juan@micorreo.cl',
    'name': 'juan muñoz',
    'role': 2,
    'login' : datetime.now(),
    }
    return render(request, 'messages/messageresponded.html',{'datos': context})

# DENNISSE SECTION

#Creacion de tareas subordinada renderizado del template
def TareaSubordinadaSection(request):
    if authenticated(request):
        # Return Section
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Content-Type':'application/json', 'Authorization': 'Bearer '+ token}
        dataAPI = requests.get(API+'TareaSubordinada', headers=headers).json()
        listTareaSubordinada = dataAPI['data']

        # Variables con data a enviar a la vista
        
        context = {
            'menu' : 'TareaSubordinadaSection',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            'tareaSubordinada': listTareaSubordinada
        }
        return render(request, 'subordinatetask/list_subordinatetask.html', {'datos': context})
    else: 
        return redirect('login')

def AddTareaSubordinadaSection(request):
    if authenticated(request):
        # Consumo de API: Tarea 
        # Method: GET
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Content-Type':'application/json', 'Authorization': 'Bearer '+ token}
        resTarea = requests.get(API+'tarea', headers=headers)
        dataTarea = resTarea.json()
        listTarea = dataTarea['data']

        # Consumo de API: Prioridad Tarea
        # Method: GET
        resPrioridad = requests.get(API+'prioridadTarea', headers=headers)
        dataPrioridad = resPrioridad.json()
        listPrioridad = dataPrioridad['data']

        # Consumo de API: Estado Tarea
        # Method: GET
        resEstado = requests.get(API+'estadoTarea', headers=headers)
        dataEstado = resEstado.json()
        listEstado = dataEstado['data']

        # Consumo de API: Tarea Subordinada
        nombre = request.POST.get('nombreTareaSubordinada')
        descripcion = request.POST.get('descripcionTareaSubordinada')
        prioridadFk = request.POST.get('prioridadtarea')
        estadoFk = 1
        tareaFk = request.POST.get('selectTarea')

        status = ''
        if nombre == '' or descripcion == '' or prioridadFk == '' or estadoFk == '' or tareaFk == '' or nombre == None:
            status = 'ERROR'
        elif nombre != '' or descripcion != '' or prioridadFk != '' or estadoFk != '' or tareaFk != '' or nombre != None:
            status = 'OK'
        else: 
            status
        
        if status == 'OK':
            AddTareaSubordinada(request, nombre, descripcion, prioridadFk, estadoFk, tareaFk)
            return redirect('TareaSubordinadaSection')

        # Variables con data para enviar a la vista
        context = {
            'menu' : 'AddTareaSubordinadaSection',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            'tarea': listTarea,
            'prioridad': listPrioridad,
            'estado': listEstado,
            'statusCreation': status,
            'listPrioridadTarea': listPrioridad
        }

        # Return Section
        return render(request, 'subordinatetask/subordinatetask.html', {'datos': context})
    
    else: 
        return redirect('login')

def DeleteTareaSubordinadaSection(request, idTareaSub):
    if authenticated:
        status = 'NO_CONTENT'
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }

        # Consumo de API: Tarea Subordinada
        # Method: DELETE
        tareaSub = str(idTareaSub)
        payload = json.dumps({'idTareaSubordinada': tareaSub})
        r = requests.delete(API+'TareaSubordinada/delete/' + tareaSub, headers=headers, data=payload)

        # Consumo de API: Tarea Subordinada
        # Method: GET
        reqTareaSubordinada = requests.get(API+'TareaSubordinada', headers=headers)
        dataAPI = reqTareaSubordinada.json()
        listTareaSubordinada = dataAPI['data']

        context = {
            'tareaSubordinada': listTareaSubordinada,
            'deleteStatus': status
        }

        if r.ok:
            status = 'DELETED'
            return redirect('TareaSubordinadaSection')
        else: 
            status = 'ERROR'
            return render(request, 'subordinatetask/list_subordinatetask.html', {'datos': context})
        
    else:
        return redirect('login')

def EditTareaSubordinadaSection(request, idTareaSub):
    if authenticated:

        # Configuración Header
        status = 'NO_CONTENT'
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }

        # Consumo de API: Tarea
        # Method: GET
        resTarea = requests.get(API+'tarea', headers=headers)
        dataTarea = resTarea.json()
        listTarea = dataTarea['data']

        # Consumo de API: OneTareaSubordinada
        # Method: GET with Params
        tareaSub = str(idTareaSub)
        resOneTareaSub = requests.get(API+'TareaSubordinada/oneTareaSubordinada/'+ tareaSub, headers=headers)
        dataTareaSub = resOneTareaSub.json()
        OneTareaSubordinada = dataTareaSub['data']

        # Consumo de API: Estado Tarea
        # Method: GET
        resEstado = requests.get(API+'estadoTarea', headers=headers)
        dataEstado = resEstado.json()
        listEstado = dataEstado['data']

        # Consumo de API: Prioridad Tarea
        # Method: GET
        resPrioridad = requests.get(API+'prioridadTarea', headers=headers)
        dataPrioridad = resPrioridad.json()
        listPrioridad = dataPrioridad['data']

        # Asignación del ID de Tarea Subordinada a Buscar
        idTareaSubordinadaToSearch = ''
        for x in OneTareaSubordinada:
            idTareaSubordinadaToSearch = x['idTareaSubordinada']
           # print(idTareaSubordinadaToSearch)
        

        # Validate Data Extraction
        if request.method == 'POST':
            try:
                #Recuperación de data proveniente del HTML
                nombre = request.POST.get('nombreTareaSubordinada')
                descripcion = request.POST.get('descripcionTareaSubordinada')
                prioridadFk = request.POST.get('prioridadtarea')
                estadoFk = request.POST.get('estadoTarea')
                tareaFk = request.POST.get('selectTarea')
                status = 'OK'
                #print(nombre, descripcion, tareaFk)
            except:
                status = 'ERROR'

        # Método Update User
        try:
            if status == 'OK':
                EditTareaSubordinada(request, nombre, descripcion, prioridadFk, estadoFk, tareaFk, idTareaSubordinadaToSearch)
                return redirect('TareaSubordinadaSection')
            
        except:
            status = 'ERROR'
        context = {
            'menu' : 'EditTareaSubordinadaSection',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
            'tarea': listTarea,
            'statusUpdate': status,
            'oneTareaSubordinada': OneTareaSubordinada[0],
            'listPrioridadTarea': listPrioridad,
            'listEstadoTarea':listEstado,
        }

        # Return Section
        # return render(request, 'subordinatetask/updatesubordinatetask.html', {'datos':context})
        return render(request, 'subordinatetask/subordinatetask.html', {'datos':context})
        
        

    else:
        return redirect('login')



# Métodos Complementarios
# --------------------------------------------
# CRUD: Tarea Subordinada

# METHOD: POST
def AddTareaSubordinada(request, nombre, descripcion, prioridadFk, estadoFk, tareaFk):
    if authenticated:
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+token, 'Accept': '*/*' }

        # Datos a enviar a la petición POST
        payload = json.dumps({'nombreSubordinada' : nombre,
                              'descripcionSubordinada': descripcion,
                              'fkPrioridadTarea': int(prioridadFk),
                              'fkEstadoTarea': int(estadoFk),
                              'fkIdTarea': int(tareaFk),
        })
        r = requests.post(API+'TareaSubordinada/add', headers=headers, data=payload)


# METHOD: PUT
def EditTareaSubordinada(request, nombre, descripcion, prioridadFk, estadoFk, tareaFk, idTareaSubordinadaToSearch):
    if authenticated:
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }


        # Datos a enviar a la petición PUT
        payload = json.dumps({'nombreSubordinada' : nombre,
                              'descripcionSubordinada': descripcion,
                              'fkPrioridadTarea': int(prioridadFk),
                              'fkEstadoTarea': int(estadoFk),
                              'fkIdTarea': int(tareaFk),
        })

        r = requests.put(API+'TareaSubordinada/update/' + str(idTareaSubordinadaToSearch), headers=headers, data=payload)


# Método para Aceptar Tareas
def AcceptTask(request, idTask):
    if authenticated:
        try:
            token = request.COOKIES.get('validate')
            headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }
            reqAcceptTask = requests.put(API+'tarea/acceptTask/' + idTask, headers=headers)
            print(reqAcceptTask)
            return redirect('taskfuncionario')

        except:
            print('ERROR')
    
    else: 
        redirect('login')


# Metodo Rechazar

def RejectTask(request, idTask):
    if authenticated:                
        try:
            descripcion = request.POST.get('descripcion')
            status = ''
            if descripcion == '':
                status = 'ERROR'
            elif descripcion != '':
                status = 'OK'
            else:
                status           
            
            if  status == 'OK':
                Addjustificacion(request,descripcion,idTask)
                return redirect('taskfuncionario')
        except:
            return redirect('taskfuncionario')
    
    else: 
        redirect('login')


def Addjustificacion(request,description,idTask):
    if authenticated:
        token = request.COOKIES.get('validate')
        
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }
        tarea = requests.get(API+'tarea/oneTask/' + idTask, headers=headers).json()
        prioridad = requests.get(API+'prioridadTarea', headers=headers).json()
        user = requests.get(API+'usuario/oneUser/'+str(tarea['data'][0]['creadaPor']), headers=headers).json()
        userRechazado = requests.get(API+'usuario/oneUser/'+str(tarea['data'][0]['fkRutUsuario']), headers=headers).json()
        
        # Datos a enviar a la petición POST
        payload = json.dumps({
            'Descripcion': description,
        })
        r = requests.post(API+'justificacionTarea/add/' + idTask, headers=headers, data=payload)
        if r.status_code == 201:
            
            data = {
                'evento': 'Tarea Rechazada', 
                'email': user['data'][0]['correoElectronico'],
                'user': user['data'][0]['nombreUsuario'] +' '+ user['data'][0]['apellidoUsuario'],
                'tarea': tarea['data'][0],
                # 'prioridad': list(e for e in prioridad['data'] if e['idPrioridad']  == tarea['data'][0]['fkPrioridadTarea'])[0]['descripcion'],
                'rechazadoPor': userRechazado['data'][0]['nombreUsuario'] +' '+ userRechazado['data'][0]['apellidoUsuario'],
                'motivo': description, 
            }
            sendEmailTask.delay(data)





#CRUD EMPRESA Alejandro
def EmpresasList(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        empresas = requests.get(API+'business/',headers=headers).json()
        listEmpresa = empresas['data']
        data = decodered(token)

        context = {
            'menu': 'EmpresasList',
            'empresas': listEmpresa,
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
        }

        return render(request, 'empresa/list_empresa.html',{'datos':context})
    else: 
        return redirect('login')

def AddEmpresaSection(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}

        rutEmpresa = request.POST.get('rutEmpresa')
        razonSocial = request.POST.get('razoSocial')
        giroEmpresa = request.POST.get('giroEmpresa')
        direccionEmpresa = request.POST.get('direccionEmpresa')
        telefono = request.POST.get('numeroTelefono')
        correoElectronico = request.POST.get('correoElectronicoEmpresa')

        status = ''
        if rutEmpresa == '' or razonSocial == '' or giroEmpresa == '' or direccionEmpresa == '' or telefono == None or correoElectronico == '':
            status = 'ERROR'
        elif rutEmpresa != '' or razonSocial != '' or giroEmpresa != '' or direccionEmpresa != '' or telefono != None or correoElectronico != '':
            status = 'OK'
        else:
            status
        if  status == 'OK':
            AddEmpresa(request,rutEmpresa,razonSocial,giroEmpresa,direccionEmpresa,telefono,correoElectronico)
        
        context = {
            'menu': 'AddEmpresaSection',
            'email' : data['email'],
            'name': data['unique_name'],
            'role': int(data['role']),
            'login' : datetime.fromtimestamp(data['nbf']),
        }
        return render(request,'empresa/new_empresa.html', {'datos':context})
    else:
        return redirect('login')


def AddEmpresa(request,rutEmpresa,razonSocial,giroEmpresa,direccionEmpresa,telefono,correoElectronico):
    if authenticated:
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }

        payload = json.dumps({
                                'rutEmpresa':rutEmpresa,
                                'razonSocial':razonSocial,
                                'giroEmpresa':giroEmpresa,
                                'direccionEmpresa':direccionEmpresa,
                                'numeroTelefono':int(telefono),
                                'correoElectronicoEmpresa':correoElectronico,
        })

        r = requests.post(API+'business/add/', headers=headers, data=payload)

def EditEmpresaSection(request, rutEmpresa):
    if authenticated(request):
        status = 'NO_CONTENT'
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }

        #consumo de API: oneEmpresa
        # method: get with params
        rutEmpresaP=str(rutEmpresa)
        resOneEmpresa = requests.get(API+'business/oneBusiness/'+ rutEmpresaP, headers=headers).json()
        #dataOneTarea = resOneTarea.json()
        OneEmpresa = resOneEmpresa['data']

        # ASignacion del rut a buscar
        empresaToSearch = ''
        for x in OneEmpresa:
            empresaToSearch = x['rutEmpresa']

        # validate data Extraction
        if request.method == 'POST':
            try:
                rutEmpresa = request.POST.get('rutEmpresa')
                razonSocial = request.POST.get('razoSocial')
                giroEmpresa = request.POST.get('giroEmpresa')
                direccionEmpresa = request.POST.get('direccionEmpresa')
                numeroTelefono = request.POST.get('numeroTelefono')
                correoElectronicoEmpresa = request.POST.get('correoElectronicoEmpresa')
                status = 'OK'
            except:
                status = 'ERROR'
        
        # metodo update User
            try:
             if status == 'OK':
              EditEmpresa(request,rutEmpresa,razonSocial,giroEmpresa,direccionEmpresa,numeroTelefono,correoElectronicoEmpresa,empresaToSearch)
            except:
                status = 'ERROR'
        #print(nombreTarea,description,dateDeadline,problem_report,assignment,responsible,justification,taskState,taskPriority)    
        context = {
            'oneEmpresa': OneEmpresa,
        }

        # return Section
        return render(request, 'empresa/edit_empresa.html', {'data':context})
    else:
        return redirect('login')


def EditEmpresa(request,rutEmpresa,razonSocial,giroEmpresa,direccionEmpresa,numeroTelefono,correoElectronicoEmpresa,empresaToSearch):

    if authenticated:
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }

        
        payload = json.dumps({
                                'rutEmpresa':rutEmpresa,
                                'razonSocial':razonSocial,
                                'giroEmpresa': giroEmpresa,
                                'direccionEmpresa': direccionEmpresa,
                                'numeroTelefono' : int(numeroTelefono),
                                'correoElectronicoEmpresa' : correoElectronicoEmpresa,
        })
        
        print(payload)
        r = requests.put(API+'business/update/'+empresaToSearch, headers=headers, data=payload)
        print(r)


def DeleteEmpresaSection(request, rutEmpresa):
    if authenticated:
        status = 'NO_CONTENT'
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }

        # Consumo de API: Empresa
        # METHOD: DELETE
        payload = json.dumps({'rutEmpresa': rutEmpresa})
        r = requests.delete(API+'business/delete/' + rutEmpresa, headers=headers, data=payload)

        # Consumo API: Empresa
        reqEmpresa = requests.get(API+'business', headers=headers)
        dataAPI = reqEmpresa.json()
        listEmpresa = dataAPI['data']

        context = {
            'empresa': listEmpresa, 
            'deleteStatus': status
        }

        if r.ok:
            status = 'DELETED'
            print(status)
            return redirect('EmpresaList')
        else:
            status = 'ERROR'
            print(status)
            return render(request, 'Empresas/list_empresa.html', {'data': context})
    
    else:
        return redirect('login')



def ViewEmpresa(request, id):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        resOneEmpresa = requests.get(API+'business/oneBusiness/'+str(id), headers=headers).json()
        OneEmpresa = resOneEmpresa['data']

        # ASignacion del rut a buscar
        empresaToSearch = ''
        for x in OneEmpresa:
            empresaToSearch = x['rutEmpresa']

        print(OneEmpresa)

        context = {
            'oneEmpresa': OneEmpresa,
        }
        return render(request, 'empresa/detail_empresa.html',{'datos': context})
    else: 
        return redirect('login')


def ProgressTask(request, idTask):
    if authenticated(request):
        status = 'NO_CONTENT'
        token = request.COOKIES.get('validate')
        data = decodered(token)
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'Authorization': 'Bearer '+token}
        

        if request.method == 'POST':
            try:
                if(int(request.POST.get('progreso')) > 0):
                    horaAvance = request.POST.get('progreso')
                    status = 'OK'
            except:
                status = 'ERROR'
            
            # Este está OK
            #print(status)
            
            try:
                
                if status == 'OK':
                    EnviarProgreso(request, idTask, horaAvance)
                    print('pasa')
                    
            except:
                status = 'ERROR'

            

        return redirect('taskfuncionario')       
    else:
        return redirect('login')

def EnviarProgreso(request,idTask,horaAvance):

    if authenticated:
        token = request.COOKIES.get('validate')
        headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Authorization': 'Bearer '+ token,'Accept': '*/*' }


        payload = horaAvance

        r = requests.put(API+'tarea/taskProgress/'+ idTask, headers=headers, data=payload)
        print(r)





# DENNISSE SECTION

