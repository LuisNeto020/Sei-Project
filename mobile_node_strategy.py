import numpy as np
import logging
import random
from geopy.distance import geodesic
from yafs.distribution import deterministicDistributionStartPoint


class MobileNodeMessageStrategy:
    def __init__(self, mobile_node_id, satellite_id):
        self.mobile_node_id = mobile_node_id
        self.satellite_id= satellite_id
        self.connected_edge_node = None  # Armazena o ID do nó EDGE atualmente conectado
        self.connected_satellite = False
        self.last_checked_time = 0       # Último timestamp processado
        self.connected_time = 0          # Tempo total conectado
        self.first_time = True
        self.disconnection_intervals = []  # Lista para armazenar intervalos de desconexão
        self.last_disconnection_start = None  # Início do intervalo atual de desconexão

    def __call__(self, sim, routing):
        if self.first_time:
            app = sim.apps["VehicleProcessing"]
            msg = app.get_message("SensorToEdge")
            sim.deploy_source("VehicleProcessing", id_node=9, msg=msg,distribution=deterministicDistributionStartPoint(210, 90, name="MessageDistri"))
            self.first_time = False
        current_time = sim.env.now  # Tempo atual na simulação
        delta_time = current_time - self.last_checked_time  # Incremento desde a última verificação
        self.last_checked_time = current_time

        # Verifica se o nó móvel está conectado a um EDGE ou satélite
        if self.connected_edge_node or self.connected_satellite:
            self.connected_time += delta_time
            if self.last_disconnection_start is not None:
                # Finaliza o intervalo de desconexão
                self.disconnection_intervals.append((self.last_disconnection_start, current_time))
                self.last_disconnection_start = None
        else:
            # Marca o início de um intervalo de desconexão, se ainda não marcado
            if self.last_disconnection_start is None:
                self.last_disconnection_start = current_time    
        self.send_message(sim)
            

    def send_message(self, sim):
        # Obtém atributos de todos os nós
        nodes = sim.topology.get_nodes_att()
        mobile_node_attrs = sim.topology.G.nodes[self.mobile_node_id]
        mobile_lat = float(mobile_node_attrs["lat"])
        mobile_lon = float(mobile_node_attrs["lon"])

        # Verifica os nós no alcance
        reachable_nodes = [
            node_id for node_id, attrs in nodes.items()
            if attrs["type"] == "EDGE" and self.is_in_range(mobile_lat, mobile_lon, attrs)
        ]

        if reachable_nodes:
            #if self.connected_satellite:
            #        self.remove_link_sat(sim)
            if self.connected_edge_node not in reachable_nodes:
            # Seleciona um nó no alcance
                target_node = random.choice(reachable_nodes)
                if self.connected_edge_node != target_node:
                    # Se o nó conectado for diferente, atualiza o link
                    self.create_link(sim, target_node)
        else:
            #if self.connected_edge_node is not None:
            #        self.remove_link(sim)
            # Verifica os satélites disponíveis no alcance
            reachable_satellites = [
                n for n, d in sim.topology.G.nodes(data=True)
                if d.get("type") == "SATELLITE" 
            ]
            #print("----------------------satelites disponiveis :", reachable_satellites)
            if  reachable_satellites:
                if self.satellite_id not in reachable_satellites:
                    # Seleciona um satélite no alcance
                    target_satellite = random.choice(reachable_satellites)
                    if self.satellite_id != target_satellite or not self.connected_satellite:
                        # Se o satélite conectado for diferente, atualiza o link
                        self.create_link_satellite(sim, target_satellite)
            else:
                # Se nenhuma conexão estiver disponível, remove os links existentes
                if self.connected_satellite:
                    self.remove_link_sat(sim)
                if self.connected_edge_node is not None:
                    self.remove_link(sim)

    def is_in_range(self, mobile_lat, mobile_lon, attrs):
        edge_lat = float(attrs["lat"])
        edge_lon = float(attrs["lon"])
        range_km = float(attrs.get("range", 5.0))  # Alcance padrão de 5 km
        
        distance = geodesic((mobile_lat, mobile_lon), (edge_lat, edge_lon)).km
        
        return distance <= range_km
    
    def create_link(self, sim, target_node):
        # Remove o link anterior, se existir
        if self.connected_edge_node is not None:
            self.remove_link(sim)
        if self.connected_satellite or self.satellite_id:
            self.remove_link_sat(sim)
        # Cria um novo link
        #sim.topology.G.add_edge(target_node, self.mobile_node_id)
        
        sim.topology.G.add_edge(self.mobile_node_id, target_node, BW= 10, PR= 10)
        self.connected_edge_node = target_node
        logging.info(f"Link criado entre o nó móvel {self.mobile_node_id} e o nó {target_node}.")
        logging.info(sim.topology.get_edge((target_node, self.mobile_node_id)))
        logging.info(list(sim.topology.G.edges(self.mobile_node_id)))
        
    
    def create_link_satellite(self, sim, target_satellite):
        # Verifica se os nós existem antes de criar o link
        if not sim.topology.G.has_node(self.mobile_node_id):
            logging.warning(f"O nó móvel {self.mobile_node_id} não existe no grafo.")
            return
        if not sim.topology.G.has_node(target_satellite):
            logging.warning(f"O satélite {target_satellite} não existe no grafo.")
            self.connected_satellite = False
            self.satellite_id = None
            return
        
        # Remove o link anterior, se existir
        if self.connected_edge_node is not None:
            self.remove_link(sim)
        if self.connected_satellite or self.satellite_id:
            self.remove_link_sat(sim)

        # Cria um novo link com o satélite alvo
        self.connected_satellite = True
        self.satellite_id = target_satellite
        sim.topology.G.add_edge(self.mobile_node_id, target_satellite, BW=100000, PR=20)
        logging.info(f"Link criado entre o nó móvel {self.mobile_node_id} e o satélite {target_satellite}.")
        logging.info(sim.topology.get_edge((target_satellite, self.mobile_node_id)))
        logging.info(list(sim.topology.G.edges(self.mobile_node_id)))
        
        
    def remove_link_sat(self, sim):
        # Verifica se os nós e a aresta existem antes de remover
        if not sim.topology.G.has_node(self.mobile_node_id):
            logging.warning(f"O nó móvel {self.mobile_node_id} não existe no grafo.")
            return
        if not sim.topology.G.has_node(self.satellite_id):
            logging.warning(f"O satélite {self.satellite_id} não existe no grafo.")
            self.connected_satellite = False
            self.satellite_id = None
            return
        if not sim.topology.G.has_edge(self.mobile_node_id, self.satellite_id):
            logging.warning(f"A aresta entre {self.mobile_node_id} e {self.satellite_id} não existe no grafo.")
            self.connected_satellite = False
            self.satellite_id = None
            return
        # Remove o link atual
        sim.topology.G.remove_edge(self.mobile_node_id, self.satellite_id)
        logging.info(f"Link removido entre o nó móvel {self.mobile_node_id} e o nó satelite {self.satellite_id}.")
        self.connected_satellite = False
        self.satellite_id = None
    
    def remove_link(self, sim):
        # Remove o link atual
        sim.topology.G.remove_edge(self.mobile_node_id, self.connected_edge_node)
        logging.info(f"Link removido entre o nó móvel {self.mobile_node_id} e o nó {self.connected_edge_node}.")
        self.connected_edge_node = None
