import numpy as np
from geopy.distance import geodesic
from geopy.point import Point
from moving_satellites import calculate_visible_satellites
import re

class MovingNodeStrategy:
    def __init__(self, node_id, start, end, total_time):
        """
        Estratégia de movimentação de um nó móvel entre dois pontos.

        :param node_id: ID do nó móvel.
        :param start: Coordenadas iniciais (x, y).
        :param end: Coordenadas finais (x, y).
        :param total_time: Tempo total para completar o movimento.
        :param area_size: Tamanho da área (opcional, para normalização).
        """
        self.node_id = node_id
        self.start = Point(start)
        self.end = Point(end)
        self.total_time = total_time
        self.current_time = 0
        self.positions = []  # Para registrar posições ao longo do tempo

    def interpolate_position(self, t):
        """
        Interpola uma posição geográfica entre o ponto inicial e final com base em t.

        :param t: Proporção do tempo (entre 0 e 1).
        :return: Nova posição interpolada (latitude, longitude).
        """
        lat_start, lon_start = self.start.latitude, self.start.longitude
        lat_end, lon_end = self.end.latitude, self.end.longitude

        # Interpolação linear (LERP) para latitude e longitude
        new_lat = lat_start + t * (lat_end - lat_start)
        new_lon = lon_start + t * (lon_end - lon_start)

        return (new_lat, new_lon)
    
    def move_node(self, sim, delta_time):
        """
        Atualiza a posição do nó com base no tempo da simulação e verifica conexão com EDGE.

        :param sim: Instância da simulação.
        :param delta_time: Incremento de tempo na simulação.
        """
        self.current_time += delta_time
        t = min(self.current_time / self.total_time, 1)  # Normaliza entre 0 e 1
        new_position = self.interpolate_position(t)
        self.positions.append(new_position)

        # Atualiza o nó na topologia
        #print("aquiiiii %s",sim.topology.G.nodes[self.node_id])
        sim.topology.G.nodes[self.node_id]["lat"] = new_position[0]
        sim.topology.G.nodes[self.node_id]["lon"] = new_position[1]


    def __call__(self, sim):
        """
        Método chamado pelo monitor da simulação.
        """
        
        delta_time = 1000  # Intervalo de tempo da simulação (ajustável)
        self.move_node(sim, delta_time)

class MovingSatelliteStrategy:
    def __init__(self, total_time, satellites, start_time, end_time, interval, cell_size, horizon_radius):
        """
        Estratégia de movimentação de um satélite entre dois pontos.

        :param node_id: ID do satélite.
        :param start: Coordenadas iniciais (x, y).
        :param end: Coordenadas finais (x, y).
        :param total_time: Tempo total para completar o movimento.
        """
        self.satellites = satellites
        self.start_time = start_time
        self.end_time = end_time
        self.interval = interval
        self.cell_size = cell_size
        self.horizon_radius = horizon_radius
        self.total_time = total_time
        self.current_time = 0
        self.positions = []  # Para registrar posições ao longo do tempo
        self.grid = None
        self.count = 0
        
    def get_satellites(self, sim):
        mobile_lat = None
        mobile_lon = None
        for node_id, attributes in sim.topology.G.nodes(data=True):
            if attributes.get("type") == "MOBILE":
                mobile_lat = attributes["lat"]
                mobile_lon = attributes["lon"]
                print(f"Nó MOBILE encontrado: ID={node_id}, Latitude={mobile_lat}, Longitude={mobile_lon}")
                break  # Remove isso se houver múltiplos nós MOBILE e você quiser verificar todos.

        return calculate_visible_satellites(mobile_lat, mobile_lon, self.satellites, self.start_time, self.end_time, self.interval, self.cell_size)

    def map_time_to_simulation(self, real_time):
        """
        Mapeia um tempo real (datetime) para o tempo de simulação em milissegundos.
        """
        delta = real_time - self.start_time
        return int(delta.total_seconds() * 1000)  # Converte para milissegundos
    
    def move_satellite(self, sim, previous_time):
        """
        Atualiza os nós de satélites na topologia com base no intervalo de tempo atual da simulação.
        :param sim: A instância da simulação.
        :param previous_time: O tempo de simulação anterior, em milissegundos.
        """
        current_sim_time = self.current_time  # Tempo de simulação atual em milissegundos
        
        # Itera sobre as células da grade
        for cell in self.grid:
            for satellite_info in cell["satellites"]:
                satellite_name = satellite_info["satellite"]
                #satellite_name = (re.search(r'\d+', satellite_name).group())
                visibility_time = satellite_info["time"]
                
                # Mapeia o tempo real para o tempo de simulação
                visibility_sim_time = self.map_time_to_simulation(visibility_time)
                
                # Verifica se o satélite está visível no intervalo atual de simulação
                if previous_time <= visibility_sim_time < current_sim_time:
                    lat = cell["latitude"]
                    lon = cell["longitude"]
                    
                    if satellite_name not in sim.topology.G.nodes:
                        # Criar nó se não existir
                        sim.topology.G.add_node(satellite_name, lat=lat, lon=lon, type="SATELLITE", IPT= 1, RAM=10, range= 30)
                        sim.topology.G.add_edge(5, satellite_name, BW= 100000, PR= 20)
                        sim.topology.G.add_edge(7, satellite_name, BW= 100000, PR= 20)
                        sim.topology.G.add_edge(6, satellite_name, BW= 100000, PR= 20)
                        app = sim.apps["VehicleProcessing"]
                        services = app.services
                        sim.deploy_module("VehicleProcessing", "SensorModule", services["SensorModule"], [satellite_name])
                        sim.deploy_module("VehicleProcessing", "SensorModuleV", services["SensorModuleV"], [satellite_name])
                    else:
                        # Atualizar posição se o nó já existir
                        sim.topology.G.nodes[satellite_name]["lat"] = lat
                        sim.topology.G.nodes[satellite_name]["lon"] = lon

        # Remover nós que não estão mais visíveis
        
        existing_satellites = [n for n, d in sim.topology.G.nodes(data=True) if d.get("type") == "SATELLITE"]
        for satellite_name in existing_satellites:
            if all(
                satellite_name != info["satellite"] or 
                not (previous_time <= self.map_time_to_simulation(info["time"]) < current_sim_time)
                for cell in self.grid for info in cell["satellites"]
            ):
                app = sim.apps["VehicleProcessing"]
                services = app.services
                des = sim.get_DES_from_Service_In_Node(satellite_name, "VehicleProcessing", "SensorModule")
                des1 = sim.get_DES_from_Service_In_Node(satellite_name, "VehicleProcessing", "SensorModuleV")
                sim.undeploy_module("VehicleProcessing", "SensorModule",des)
                sim.undeploy_module("VehicleProcessing", "SensorModuleV",des1)
                edges_to_remove = list(sim.topology.G.edges(satellite_name))
                # Remove todas as arestas
                sim.topology.G.remove_edges_from(edges_to_remove)
                #sim.topology.G.remove_edge(6, satellite_name)
                sim.topology.G.remove_node(satellite_name)
        
    def __call__(self, sim):
        """
        Método chamado pelo monitor da simulação.
        """
        if self.count == 0:
            self.grid = self.get_satellites(sim)
            print(self.grid) 
            self.count += 1
        delta_time = 60000 
        previous_time = self.current_time
        self.current_time += delta_time  # Atualiza o tempo de simulação atual
        
        #if self.grid:
        self.move_satellite(sim, previous_time)
        
        for node_id, attributes in sim.topology.G.nodes(data=True):
            # Verifica se o nó é do tipo "SATELLITE"
            if attributes.get("type") == "SATELLITE":
                latitude = attributes.get("lat", "Não disponível")
                longitude = attributes.get("lon", "Não disponível")
                range_value = attributes.get("range", "Não disponível")
                # Print as informações do satélite
                print(f"Nó SATELLITE encontrado: ID={node_id}, Latitude={latitude}, Longitude={longitude}, Alcance={range_value}")
      