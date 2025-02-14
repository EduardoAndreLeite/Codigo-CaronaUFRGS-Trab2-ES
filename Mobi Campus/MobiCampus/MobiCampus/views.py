from ast import Delete
from multiprocessing import context
from random import randint, random
from wsgiref import validate
from django.shortcuts import render, get_object_or_404,get_list_or_404, HttpResponseRedirect
from django.http import HttpResponse
from .models import Usuario, Administrador, Motorista, Carona, CaronaHist, Solicitacao
from django.contrib.auth.models import User
from django.template import loader
from django.http import Http404
from .forms import Autenticacao, Cadastro, Pedido, InsercaoViagem, AvaliacaoForm
from django.contrib.auth import authenticate, login

ORIGENSEDESTINOS=['Campus do Vale', 'Campus Centro', 'Campus Olimpico', 'Campus Saude']
RUAS=['Bento Goncalvez', 'Ipiranga', 'Dr.Salvador Franca', 'Borges de Medeiros']

#Responsavel pela view da pagina inicial
def login_page(request):
    if request.method=='POST':
        form=Autenticacao(request.POST)

        if(form.is_valid()):
            username=form.cleaned_data['login']
            password=form.cleaned_data['senha']
            user=authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                return HttpResponseRedirect('home')
            else:
                error= loader.get_template('MobiCampus/login.html')
                contexto={
                    'form': form,
                }
                return HttpResponse(error.render(contexto, request))
    else:
        form=Autenticacao()    
    
        template = loader.get_template('MobiCampus/login.html')
        contexto= {
            'form': form,
        }

    return HttpResponse(template.render(contexto, request))


def create_new_user(form):
    username = form.cleaned_data['login']
    password = form.cleaned_data['senha']
    nome=form.cleaned_data['primeiro_nome']
    sobrenome=form.cleaned_data['sobrenome']

    is_motorista = form.cleaned_data['motorista_check']
    if is_motorista:
        cnh = form.cleaned_data['cnh']
        novo_motorista = Motorista.objects.create_motorista(username, password, cnh, first_name=nome, last_name=sobrenome)
        return novo_motorista
    else:
        novo_usuario = Usuario.objects.create_usuario(username, password, first_name=nome, last_name=sobrenome)
        return novo_usuario

def signup_page(request):
    if request.method=='POST':
        form=Cadastro(request.POST)
        if(form.is_valid()):
            new_user = create_new_user(form)
            login(request, new_user.user)
            return HttpResponseRedirect('home')
        else:
            template = loader.get_template('MobiCampus/signup.html')
            contexto= {
                'form': form,
            }
            return HttpResponse(template.render(contexto, request))
    else:
        form=Cadastro()    
    
        template = loader.get_template('MobiCampus/signup.html')
        contexto= {
            'form': form,
        }

    return HttpResponse(template.render(contexto, request))

#Responsável pela view da pagina do usuario
from django.contrib.auth.decorators import login_required

@login_required
def detail(request):
    template = loader.get_template('MobiCampus/detail.html')
    contexto={
        'user':request.user,
        'motor': request.user.usuario in Usuario.objects.filter(motorista__isnull=False),
        'motorUser': Motorista.objects.get(user=request.user) if request.user.usuario in Usuario.objects.filter(motorista__isnull=False) else None,
    }

    return HttpResponse(template.render(contexto, request))

#Responsavel pela view da página de um motorista
@login_required
def motorista_detail(request):
    user=request.user

    template=loader.get_template('MobiCampus/Pag_Motorista.html')

    contexto={
        'Motorista':user,
    }
    
    return HttpResponse(template.render(contexto, request))


#responsável pela view da página de busca 
@login_required
def buscando_viagem(request):
    if(Solicitacao.objects.filter(Passageiro=request.user.usuario, Aceito=True).count()!=0):
        return HttpResponseRedirect('/MobiCampus/passageiro_em_viagem/')
    
    if(request.method=='POST'):
        form=Pedido(request.POST)

        if(form.is_valid()):
            origem=form.cleaned_data['origem']
            destino=form.cleaned_data['destino']
            tempo=form.cleaned_data['tempo']

            return resultado(request, origem, destino, tempo)
    else:
        form=Pedido(request.POST)
    
    template = loader.get_template('MobiCampus/buscar_viagem.html')

    contexto={
        'form':form,
    }
    return HttpResponse(template.render(contexto, request))

def resultado(request, origem, destino, tempo):
    
    #regex para achar uma rota que contenha a origem e destino nesta ordem
    matcher='[a-zA-Z ,.]*'+origem+'[a-zA-Z ,.]*'+destino+'[a-zA-Z ,.]*'

    caronas=Carona.objects.filter(rota__regex=matcher,passageiros__lt=4,tempo__lte=tempo, finalizada=False).values()
    template=loader.get_template('MobiCampus/resultados_busca.html')

    contexto={
        'caronas':caronas,
        'rotas':matcher,
    }
    
    return HttpResponse(template.render(contexto, request))

#Devolve uma rota aleatória
def randomizador_rota(origem, destino):
    maximo=len(RUAS)-1
    rota=origem+','+RUAS[randint(0, maximo)]+','+RUAS[randint(0, maximo)]+','+destino

    return rota

#Realiza a inserção de uma viagem no sistema
@login_required
def CriarNovaCarona(request):
    template=loader.get_template('MobiCampus/CriaNovaCarona.html')  
    user=request.user

    if(Carona.objects.filter(motorista=user.usuario.motorista, finalizada=False).count()!=0):
        return HttpResponseRedirect('Em_Viagem')

    if(request.method=='POST'):
        form=InsercaoViagem(request.POST)

        if(form.is_valid()):
           origem=form.cleaned_data['origem']
           destino=form.cleaned_data['destino']
           tempo=form.cleaned_data['tempo']
           rota=randomizador_rota(origem, destino)

           if (origem in ORIGENSEDESTINOS and destino in ORIGENSEDESTINOS):
                viagem=Carona(origem=origem, destino=destino,passageiros=0, rota=rota, tempo=tempo, motorista=user.usuario.motorista, custo=randint(1, 25))
                viagem.save()
                hist_inst=CaronaHist(user=request.user.usuario, carona=viagem, status='Motorista')
                hist_inst.save()

                return HttpResponseRedirect('Em_Viagem')
           else:
                context=  { 
                    'form': form,
                    'comecado':False,
                    'erro': False, 
                    }
                return HttpResponse(template.render(context, request))
    else:
        form=InsercaoViagem()
  
    context=  { 
        'form': form,
        'comecado':False,
        'erro': False, 
        }

    return HttpResponse(template.render(context, request))

#responsável pela view do historico de viagens 
@login_required
def historico_viagem(request):
    user = request.user
    caronas = CaronaHist.objects.filter(user=user.usuario).values()
    setOfCaronaIds = [carona['carona_id'] for carona in caronas]
    viagens = []
    for id in setOfCaronaIds:
        viagens.append(Carona.objects.filter(caronaId = id).values()[0])

    contexto={
        'historico_list':viagens,
    }
    
    template=loader.get_template('MobiCampus/historico_viagem.html')
    return HttpResponse(template.render(contexto, request))

@login_required
#função a ser ativada quando o usuário for pedir uma corrida 
def Solicitar_Carona(request, carona):
    user=request.user
    Motorista=Carona.objects.get(pk=carona).motorista

    if(Solicitacao.objects.filter(Passageiro=user.usuario).count()!=0):
        return HttpResponseRedirect('/MobiCampus/pedido/aguardando/')

    sol=Solicitacao.objects.create(Passageiro=user.usuario, Motorista=Motorista, Carona=Carona.objects.get(pk=carona))
    sol.save()
    return HttpResponseRedirect('/MobiCampus/pedido/aguardando/')

@login_required
def Em_Viagem(request):
    user=request.user
    solicitacoes=Solicitacao.objects.filter(Motorista=user.usuario)
    carona=Carona.objects.get(motorista=user.usuario, finalizada=False)
    passageiros=CaronaHist.objects.filter(carona=carona, status='Passageiro')

    template=loader.get_template('MobiCampus/tabela_html.html')

    context={
        'Pedidos':solicitacoes,
        'Passageiros':passageiros,
        'viagem': carona,
    }

    return HttpResponse(template.render(context, request))

@login_required
def Aguardar(request):
    Pedido=Solicitacao.objects.filter(Passageiro=request.user.usuario)

    template=loader.get_template('MobiCampus/Aguardando.html')
    
    if(not Pedido):
        aceito=False
    else:
        aceito=Pedido.values()[0]['Aceito']

    contexto={
        'Pedido':Pedido,
        'Aceito':aceito,
    }

    return HttpResponse(template.render(contexto, request))

@login_required
def Aceitar_Carona(request, identificador):
    Pedido=Solicitacao.objects.get(Id=identificador)
    Pedido.Aceito=True
    Pedido.save()
    user=request.user
    motorista=user.usuario.motorista
    carona=Carona.objects.get(motorista=motorista, finalizada=False)
    hist_inst=CaronaHist(user=Pedido.Passageiro, carona=carona, status='Passageiro')
    hist_inst.save()
    carona.passageiros+=1
    carona.save()

    return HttpResponseRedirect('/MobiCampus/motorista/Em_Viagem')

@login_required
def Negar_Carona(request, identificador):
    Solicitacao.objects.get(Id=identificador).delete()

    return HttpResponseRedirect('/MobiCampus/motorista/Em_Viagem')

@login_required
def Finalizar_Carona(request):
    
    user=request.user
    solicitacoes=Solicitacao.objects.filter(Motorista=user.usuario.motorista)
    #for solicitacao in solicitacoes:
    #    solicitacao.delete()

  
    carona =Carona.objects.get(motorista=user.usuario.motorista, finalizada=False)
    if(carona is not None):
        carona.finalizada=True
        carona.save()
    
    return HttpResponseRedirect('/MobiCampus/avaliacao')

@login_required
def Finalizar_Carona_Motorista(request):
    print("here")
    user=request.user
    solicitacoes=Solicitacao.objects.filter(Motorista=user.usuario.motorista)
    #for solicitacao in solicitacoes:
    #    solicitacao.delete()

  
    carona =Carona.objects.get(motorista=user.usuario.motorista, finalizada=False)
    if(carona is not None):
        carona.finalizada=True
        carona.save()
    
    return HttpResponseRedirect('/MobiCampus/home')

@login_required
def Avaliacao(request):
    
    if request.method=='POST':
        form=AvaliacaoForm(request.POST)

        if(form.is_valid()):
            ratingCh=form.cleaned_data.get("RATING")
            print(ratingCh)

        user=request.user
        solicitacoes=Solicitacao.objects.filter(Passageiro=user.usuario)

        cnh = Solicitacao.objects.get(Passageiro=user.usuario).Motorista.cnh
        totalNotas = Motorista.objects.get(cnh=cnh).totalNotas
        
        Motorista.objects.filter(cnh=cnh).update(totalNotas = totalNotas+1)
        totalNotas += 1
        print(totalNotas)
        motoristaRating = Motorista.objects.get(cnh=cnh).rating
        Motorista.objects.filter(cnh=cnh).update(rating = (motoristaRating*(totalNotas-1)+int(ratingCh))/(totalNotas))
        print(cnh)


        for solicitacao in solicitacoes:
            solicitacao.delete()


        return HttpResponseRedirect('/MobiCampus/home')
    else:
        form=AvaliacaoForm()    
    
        template = loader.get_template('MobiCampus/avaliacao.html')
        contexto= {
            'form': form,
        }
        
    return HttpResponse(template.render(contexto, request))

def Viajando(request):
    
    template=loader.get_template('Mobicampus/page_viagem_user.html')
    
    contexto={
        'usuario':request.user,
    }

    return HttpResponse(template.render(contexto,request))





