import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import random
from pathlib import Path
import json
import logging.config
from yafs.core import Sim
from yafs.application import Application,Message,fractional_selectivity,create_applications_from_json
from yafs.topology import Topology
from yafs.placement import JSONPlacement
from yafs.path_routing import DeviceSpeedAwareRouting
from yafs.distribution import deterministic_distribution,deterministicDistributionStartPoint
from moving_strategy import MovingNodeStrategy, MovingSatelliteStrategy
from mobile_node_strategy import MobileNodeMessageStrategy
from matplotlib.animation import PillowWriter
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

from datetime import timedelta, datetime
from sgp4.earth_gravity import wgs84
from skyfield.api import load, Topos, EarthSatellite, wgs84
import json

def create_video(folder_results, topology_data, positions_file, satellite_positions_file, area_size=(-14.81, -46.81)):
    """
    Cria uma animação mostrando o movimento de um nó móvel e um satélite.
    
    :param folder_results: Caminho da pasta para salvar o GIF.
    :param topology_data: Dados da topologia contendo nós estáticos.
    :param positions_file: Arquivo com as posições do nó móvel (CSV).
    :param satellite_positions_file: Arquivo com as posições do satélite (CSV).
    :param area_size: Tamanho da área de visualização.
    """
    # Carregar as posições do nó móvel e do satélite
    positions = np.loadtxt(positions_file, delimiter=",")
    satellite_positions = np.loadtxt(satellite_positions_file, delimiter=",")
    
    fig, ax = plt.subplots(figsize=(8, 8))

    ax.set_xlim(-15.0, area_size[0])
    ax.set_ylim(-47.0, area_size[1])
    ax.set_xlabel("Latitude (km)")
    ax.set_ylabel("Longitude (km)")

    

    # Carregar ícones
    mobile_node_icon = plt.imread("car_endpoint.png")  # Caminho do ícone do nó móvel
    satellite_icon = plt.imread("satelite.png")  # Caminho do ícone do satélite
    static_icon = plt.imread("endpoint.png")  # Caminho do ícone do satélite
    

    def create_icon(image, position, zoom=0.5):
        """Cria um ícone no gráfico."""
        icon = OffsetImage(image, zoom=zoom)
        box = AnnotationBbox(icon, position, frameon=False)
        ax.add_artist(box)
        return box
    def create_icon_sat(image, position, zoom=0.1):
        """Cria um ícone no gráfico."""
        icon = OffsetImage(image, zoom=zoom)
        box = AnnotationBbox(icon, position, frameon=False)
        ax.add_artist(box)
        return box

    # Adicionar nós estáticos com ícones
    static_nodes = [(node["id"], node.get("lat", random.uniform(0, area_size[0])),
                     node.get("lon", random.uniform(0, area_size[1])), node.get("range", 0))
                    for node in topology_data["entity"]
                    if node.get("type") == "EDGE"
                    ]

    static_node_boxes = []
    for node_id, lat, lon, coverage_range in static_nodes:
        # Adicionar ícone do nó estático
        box = create_icon(static_icon, (lat, lon))
        static_node_boxes.append(box)
        # Adicionar círculo de cobertura, se necessário
        if coverage_range > 0:
            ax.add_patch(plt.Circle((lat, lon), coverage_range, color='blue', alpha=0.3, label=f"Coverage Node {node_id}"))


    # Inicializar ícones no gráfico
    mobile_node_box = create_icon(mobile_node_icon, (positions[0, 0], positions[0, 1]))
    satellite_box = create_icon_sat(satellite_icon, (satellite_positions[0, 0], satellite_positions[0, 1]))

    satellite_range_circle = plt.Circle((satellite_positions[0, 0], satellite_positions[0, 1]), 
                                        5.0, color='green', alpha=0.3, label="Satellite Range")
    ax.add_patch(satellite_range_circle)  # Adicionar o círculo do alcance do satélite

    def update(frame):
        # Atualizar posições do nó móvel e do satélite
        mobile_node_box.xybox = (positions[frame, 0], positions[frame, 1])
        satellite_box.xybox = (satellite_positions[frame, 0], satellite_positions[frame, 1])
        satellite_range_circle.set_center((satellite_positions[frame, 0], satellite_positions[frame, 1]))
        return mobile_node_box, satellite_box, satellite_range_circle

    # Criar animação
    writer = PillowWriter(fps=30)
    ani = FuncAnimation(fig, update, frames=min(len(positions), len(satellite_positions)), interval=100, blit=True)

    # Salvar como GIF
    ani.save(folder_results + "moving_node_and_satellite_simulation.gif", writer=writer)
    plt.show()





def main(experimento, stop_time, it, folder_results):
    """
    TOPOLOGY from a json
    """
    t = Topology()
    dataNetwork = json.load(open(experimento+'network.json'))
    t.load(dataNetwork)
    
    mobile_node_id = max([node["id"] for node in dataNetwork["entity"]]) + 1
    t.G.add_node(mobile_node_id, type="MOBILE", lon="-15.0",lat= "-47.0",IPT= 1, RAM=10)
    satellite_node_id = 10
    #t.G.add_node(satellite_node_id, type="SATELLITE", lon="0",lat= "0",IPT= 1, RAM=10, range= 5)
    #t.G.add_edge(satellite_node_id, 7, PR= 20, BW=200000)
    """
    APPLICATION
    """
    dataApp = json.load(open(experimento+'appDefinition.json'))
    apps = create_applications_from_json(dataApp)
    for app in apps:
        print(apps[app])
        print(apps[app].messages)
       
    """
    PLACEMENT algorithm
    """
    placementJson = json.load(open(experimento+'allocDefinition.json'))
    placement = JSONPlacement(name="Placement",json=placementJson)

    """
    Defining ROUTING algorithm to define how path messages in the topology among modules
    """
    selectorPath = DeviceSpeedAwareRouting()

    """
    SIMULATION ENGINE
    """
    s = Sim(t, default_results_path=folder_results+f"sim_trace_{it}")

    """
    Deploy services == APP's modules
    """
    for aName in apps.keys():
        s.deploy_app(apps[aName], placement, selectorPath)
        
    """
    Deploy mobile user
    """
    #app_user = s.apps["VehicleProcessing"]
    #msg_user = app_user.get_message("SensorToEdge") 
    #s.deploy_source(app_user, mobile_node_id, msg_user, distribution=deterministic_distribution(50,name="MessageDistri"))
        
    message_strategy = MobileNodeMessageStrategy(
        mobile_node_id=mobile_node_id,
        satellite_id= None,
    )

    dist_message = deterministicDistributionStartPoint(700,700, name="MessageDistribution")
    s.deploy_monitor("MobileNodeMessageStrategy", message_strategy, dist_message, **{"sim": s, "routing": selectorPath})
        
    moving_strategy = MovingNodeStrategy(
        node_id=mobile_node_id,
        start=(-15.0, -47.0),
        #end=(-15.0, -47.0),
        end=(-14.81, -46.81),
        total_time=stop_time
    )

    # Configura um monitor para a movimentação
    dist = deterministicDistributionStartPoint(0, 1000, name="MoveDistribution")
    s.deploy_monitor("MovingNode", moving_strategy, dist, **{"sim": s})
    
    #download the latest file
    max_days = 7.0         # download again once 7 days old
    name = 'Starlink.json'

    base = 'https://celestrak.org/NORAD/elements/gp.php'
    url = base + '?GROUP=Starlink&FORMAT=json'

    if not load.exists(name) or load.days_old(name) >= max_days:
        load.download(url, filename=name)

    #Loading satellite elements

    with load.open('Starlink.json') as f:
        data = json.load(f)

    ts = load.timescale()
    sats = [EarthSatellite.from_omm(ts, fields) for fields in data]
    print('Loaded', len(sats), 'satellites')
    
    cell_size = 1.0  # Tamanho da célula da grade em graus
    horizon_radius = 5.0  # Raio do horizonte visível em graus
    start_time = datetime.utcnow()  # Tempo de início da simulação
    end_time = start_time + timedelta(minutes=10)  # Simular por 1 hora
    interval = timedelta(minutes=1)  # Atualizar a cada 10 minutos
    
    moving_satellite_strategy = MovingSatelliteStrategy(
        satellites = sats,
        start_time = start_time,
        end_time = end_time,
        interval = interval,
        cell_size = cell_size,
        horizon_radius = horizon_radius,
        total_time=stop_time
    )

    # Configura um monitor para a movimentação
    dist = deterministicDistributionStartPoint(0, 60000, name="MoveDistribution")
    s.deploy_monitor("MovingSatelliteNode", moving_satellite_strategy, dist, **{"sim": s})
    


    """
    RUNNING - last step
    """
    logging.info(" Performing simulation: %i " % it)
    s.run(stop_time)  # To test deployments put test_initial_deploy a TRUE
    s.print_debug_assignaments()
    print("unreachebled links ---->",s.unreachabled_links)
    positions = np.array(moving_strategy.positions)
    #satellite_pos = np.array(moving_satellite_strategy.positions)
    np.savetxt(folder_results + "mobile_node_positions.csv", positions, delimiter=",")
    #np.savetxt(folder_results + "satellite_node_positions.csv", satellite_pos, delimiter=",")
    
    total_time = message_strategy.last_checked_time
    connected_time = message_strategy.connected_time
    connectivity_ratio = connected_time / total_time if total_time > 0 else 0
    print(f"Conectividade total do nó móvel: {connectivity_ratio:.2%} do tempo de simulação.")
    print(total_time)
    
    
    print("desconecçoes:", message_strategy.disconnection_intervals )

    #print("Number of new users: %i"%len(evol.listUsers))
    #create_video(folder_results,dataNetwork,"results/cenario1/mobile_node_positions.csv","results/satellite_node_positions.csv")


if __name__ == '__main__':
    import os
    import pandas as pd

    LOGGING_CONFIG = Path(__file__).parent / 'logging.ini'
    logging.config.fileConfig(LOGGING_CONFIG)
    pathExperimento = "scenario1/"  # Altere conforme o diretório dos JSONs
    simulationDuration = 600000  # Duração da simulação
    folder_results = Path("results/cenario4/")
    folder_results.mkdir(parents=True, exist_ok=True)
    folder_results = str(folder_results)+"/"
    
    os.makedirs(folder_results, exist_ok=True)

    for i in range(30):
        main(pathExperimento, stop_time=simulationDuration, it=i, folder_results=folder_results)
    
    print("results:")
    # Carregar os arquivos
    eventos = pd.read_csv("results/sim_trace.csv")
    transmissions = pd.read_csv("results/sim_trace_link.csv")

    # Calcular a latência total por `id`
    # Passo 1: Adicionar a latência individual (time_reception - time_emit)
    eventos['latency'] = eventos['time_reception'] - eventos['time_emit']

    # Passo 2: Agrupar por `id` e somar as latências
    latency_per_task = eventos.groupby('id')['latency'].sum().reset_index()

    # Renomear a coluna para indicar que é a latência total
    latency_per_task.rename(columns={'latency': 'total_latency'}, inplace=True)

    # Passo 3: Calcular a latência média end-to-end (média de todas as tarefas)
    average_end_to_end_latency = latency_per_task['total_latency'].mean()
    max_latency = latency_per_task['total_latency'].max()
    min_latency = latency_per_task['total_latency'].min()

    # Exibir os resultados
    print("Latência total por tarefa:")
    print(latency_per_task)

    print("\nLatência média end-to-end:", average_end_to_end_latency)
    print("Latência máxima total:", max_latency)
    print("Latência mínima total:", min_latency)
    
    
    

    # Contar o número de transmissões registradas para cada ID
    transmissions_per_task = eventos.groupby('id').size().reset_index(name='message_count')

    expected_message_count = 6
    transmissions_per_task['missing_messages'] = expected_message_count - transmissions_per_task['message_count']
    transmissions_per_task['missing_messages'] = transmissions_per_task['missing_messages'].clip(lower=0)  # Evitar valores negativos

    # Calcular a taxa de perda de pacotes
    total_expected_messages = len(transmissions_per_task) * expected_message_count
    total_actual_messages = transmissions_per_task['message_count'].sum()
    packet_loss_rate = (total_expected_messages - total_actual_messages) / total_expected_messages

    # Exibir os resultados
    print("Transmissões por tarefa:")
    print(transmissions_per_task)

    print("\nTaxa de perda de pacotes:", packet_loss_rate)
    transmissions_per_task.to_csv("results/task_failure_analysis.csv", index=False)
    
    eventos = eventos.sort_values(by=['id', 'time_emit'])

    # Passo 3: Calcular a diferença de latência entre mensagens consecutivas para o mesmo `id`
    eventos['latency_diff'] = eventos.groupby('id')['latency'].diff().fillna(0)

    # Passo 4: Calcular o jitter (usando a média ou desvio padrão das diferenças de latência)
    # Usando o desvio padrão para jitter, pois é uma medida comum de variação
    jitter_per_task = eventos.groupby('id')['latency_diff'].std().reset_index()

    # Renomear a coluna para indicar que é o jitter
    jitter_per_task.rename(columns={'latency_diff': 'jitter'}, inplace=True)

    # Passo 5: Calcular o jitter médio, máximo e mínimo
    average_jitter = jitter_per_task['jitter'].mean()
    max_jitter = jitter_per_task['jitter'].max()
    min_jitter = jitter_per_task['jitter'].min()

    # Exibir os resultados
    print("Jitter por tarefa:")
    print(jitter_per_task)

    print("\nJitter médio:", average_jitter)
    print("Jitter máximo:", max_jitter)
    print("Jitter mínimo:", min_jitter)
    
    # Tempo total da simulação
    total_time = transmissions['ctime'].max() - transmissions['ctime'].min()

    # Throughput
    total_data_transmitted = transmissions['size'].sum()
    throughput = total_data_transmitted / total_time
    print("Throughput:", throughput, "bytes/s") 

    # Tempo total da operação
    simulation_time = eventos['time_out'].max() - eventos['time_in'].min()

    # Total de tempo ativo (somando intervalos)
    active_time = (eventos['time_out'] - eventos['time_in']).sum()

    # Disponibilidade da conexão
    connection_availability = active_time / simulation_time
    print("Disponibilidade da conexão:", connection_availability)

    
    
   
    