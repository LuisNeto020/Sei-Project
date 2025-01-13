import pandas as pd
import matplotlib.pyplot as plt
import math
import glob
from scipy.stats import t

# Definir os caminhos dos cenários
cenario1_path = "results/cenario3/*.csv"  # Substitua pelo diretório dos arquivos do cenário 1
cenario2_path = "results/cenario2/*.csv"  # Substitua pelo diretório dos arquivos do cenário 2
cenario3_path = "results/cenario4/*.csv"

# Função para processar arquivos de tarefas perdidas

def process_lost_tasks(file_pattern, simulation_time):
    all_lost_tasks = []

    for file in glob.glob(file_pattern):
        if "_link" not in file:
            continue

        data = pd.read_csv(file)

        # Calcular tarefas perdidas
        data = data.sort_values(by='ctime').drop_duplicates(subset='id', keep='first')
        data['group'] = (data['ctime'] // 10000).astype(int)
        grouped_ids = data.groupby('group').size()

        # Garantir que todos os grupos existam
        all_groups = pd.Series(0, index=range(simulation_time))
        grouped_ids = grouped_ids.reindex(all_groups.index, fill_value=0)

        def calculate_expected_ids(group_number):
            if group_number == 0:
                return max(0, math.ceil((10000 - 910) / 90))
            else:
                return math.ceil(10000 / 90)

        expected_ids = grouped_ids.index.map(calculate_expected_ids)
        lost_tasks_percentage = (1 - (grouped_ids / expected_ids)) * 100
        lost_tasks_percentage = lost_tasks_percentage.fillna(0)
        all_lost_tasks.append(lost_tasks_percentage)

    # Calcular a média de todos os testes
    avg_lost_tasks = pd.concat(all_lost_tasks, axis=1).mean(axis=1)
    return avg_lost_tasks


def process_lost_tasks_total(file_pattern):
    all_lost_tasks = []

    for file in glob.glob(file_pattern):
        if "_link" not in file:
            continue

        print("Processando arquivo:", file)
        data = pd.read_csv(file)

        # Calcular tarefas perdidas
        data = data.sort_values(by='ctime').drop_duplicates(subset='id', keep='first')
        grouped_ids = data['id'].count()

        # Calcular tarefas esperadas
        total_simulation_time = 600000
        expected_ids = math.ceil((total_simulation_time - 910) / 90)

        # Calcular porcentagem de tarefas perdidas
        lost_tasks_percentage = (1 - (grouped_ids / expected_ids)) * 100
        all_lost_tasks.append(lost_tasks_percentage)

    # Converter para uma série do pandas
    all_lost_tasks = pd.Series(all_lost_tasks)

    # Calcular as métricas
    max_lost_tasks = all_lost_tasks.max()
    min_lost_tasks = all_lost_tasks.min()
    mean_lost_tasks = all_lost_tasks.mean()

    return max_lost_tasks, min_lost_tasks, mean_lost_tasks
# Função para processar arquivos de latências

def process_latencies(file_pattern, simulation_time):
    all_latencies = []

    for file in glob.glob(file_pattern):
        if "_link" not in  file:
            continue
        print("aqui: ",file )
        data = pd.read_csv(file)

        # Calcular latência média
        #data['latency'] = data['time_reception'] - data['time_emit'] + data[]
        time_emit_per_task = data.groupby('id')['ctime'].last().reset_index()
        time_emit_per_task.rename(columns={'ctime': 'first_time_emit'}, inplace=True)
        latency_per_task = data.groupby('id')['latency'].sum().reset_index()
        latency_per_task = latency_per_task.merge(time_emit_per_task, on='id')
        latency_per_task['group'] = (latency_per_task['first_time_emit'] // 10000).astype(int)
        latency_per_group = latency_per_task.groupby('group')['latency'].mean()
        
        # Garantir que todos os grupos existam
        all_groups = pd.Series(index=range(simulation_time), dtype=float)
        latency_per_group = latency_per_group.reindex(all_groups.index)
        all_latencies.append(latency_per_group)

    # Calcular a média de todos os testes
    avg_latencies = pd.concat(all_latencies, axis=1).mean(axis=1)
    return avg_latencies

def process_latencies_total(file_pattern):
    all_latencies = []

    for file in glob.glob(file_pattern):
        if "_link" not in file:
            continue
        print("Processando arquivo:", file)
        data = pd.read_csv(file)

        # Calcular latência total para cada tarefa
        latency_per_task = data.groupby('id')['latency'].sum()
        mean_per_file = latency_per_task.mean()
        # Adicionar todas as latências à lista
        all_latencies.append(mean_per_file)

    # Converter a lista de latências em uma série do pandas
    all_latencies = pd.Series(all_latencies)

    mean_latency = all_latencies.mean()
    

    
    max_latency = all_latencies.max()
    min_latency = all_latencies.min()
    print(max_latency, min_latency)

    return max_latency, min_latency, mean_latency


# Configurações
simulation_time = 600000 // 10000

# Processar cenários para tarefas perdidas
lost_tasks_cenario1 = process_lost_tasks(cenario1_path, simulation_time)
lost_tasks_cenario2 = process_lost_tasks(cenario2_path, simulation_time)
lost_tasks_cenario3 = process_lost_tasks(cenario3_path, simulation_time)

# Processar cenários para latências
latencies_cenario1 = process_latencies(cenario1_path, simulation_time)
latencies_cenario2 = process_latencies(cenario2_path, simulation_time)
latencies_cenario3 = process_latencies(cenario3_path, simulation_time)
latencies_cenario1.loc[39:42] = float('nan')
latencies_cenario1 = latencies_cenario1.dropna()
latencies_cenario2 = latencies_cenario2.dropna()
latencies_cenario3 = latencies_cenario3.dropna()

# Plotar gráfico de tarefas perdidas
plt.figure(figsize=(10, 6))
plt.plot(lost_tasks_cenario1.index/6, lost_tasks_cenario1, marker='o', color='orange', label='Terrestrial Network')
plt.plot(lost_tasks_cenario2.index/6, lost_tasks_cenario2, marker='o', color='blue', label='Hybrid Network')
plt.plot(lost_tasks_cenario3.index/6, lost_tasks_cenario3, marker='o', color='green', label='Satellite Network')
plt.title('Percent of Lost Tasks per Simulation Time')
plt.xlabel('Simulation time (seconds)')
plt.ylabel('Tasks Lost  (%)')
plt.grid(True)
plt.legend()
plt.show()

# Plotar gráfico de latências médias
plt.figure(figsize=(10, 6))
plt.plot(latencies_cenario1.index/6, latencies_cenario1, marker='o', color='orange', label='Terrestrial Network')
plt.plot(latencies_cenario2.index/6, latencies_cenario2, marker='o', color='blue', label='Hybrid Network')
plt.plot(latencies_cenario3.index/6, latencies_cenario3, marker='o', color='green', label='Satellite Network')
plt.title('Average End-to-End Latency per Simulation Time')
plt.xlabel('Simulation time (seconds)')
plt.ylabel('Average End-to-End Latency (ms)')
plt.grid(True)
plt.legend()
plt.show()


# Dados de entrada (exemplo de padrões de arquivos para os cenários)
file_patterns = [cenario1_path, cenario2_path, cenario3_path]

# Processar os dados para cada cenário
mean_jitter = []
max_jitter = []
min_jitter = []

for pattern in file_patterns:
    max_latency, min_latency, mean_latency = process_latencies_total(pattern)
    mean_jitter.append(mean_latency)
    max_jitter.append(max_latency)
    min_jitter.append(min_latency)

# Calcular a variabilidade (erro) com base na diferença entre máximo e mínimo
error_upper = [max_val - mean_val for max_val, mean_val in zip(max_jitter, mean_jitter)]  # Máximo - Médio
error_lower = [mean_val - min_val for mean_val, min_val in zip(mean_jitter, min_jitter)]  # Médio - Mínimo

# Rótulos dos cenários
labels = ['Terrestrial', 'Hybrid', 'Satellite']

# Criar o gráfico de barras com barras de erro
bars= plt.bar(labels, mean_jitter, color=['blue', 'orange', 'green'], capsize=5)
for i, bar in enumerate(bars):
    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
             f"{mean_jitter[i]:.2f}", ha='center', fontsize=10, color='black')
# Adicionar rótulos, título e legendas
plt.xlabel('Network Infrastructure', fontweight='bold')
plt.ylabel('Latency (ms)', fontweight='bold')
plt.title('Average End-to-End Latency', fontweight='bold')

# Exibir o gráfico
plt.show()


mean_packet_loss = []
max_packet_loss= []
min_packet_loss = []
for pattern in file_patterns:
    max_loss, min_loss, mean_loss = process_lost_tasks_total(pattern)
    mean_packet_loss.append(mean_loss)
    max_packet_loss.append(max_loss)
    min_packet_loss.append(min_loss)

# Rótulos dos cenários
labels = ['Terrestrial', 'Hybrid', 'Satellite']

# Criar o gráfico de barras com barras de erro
bars = plt.bar(labels, mean_packet_loss, color=['blue', 'orange', 'green'], capsize=5, label='Average ETE Latency')
for i, bar in enumerate(bars):
    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
             f"{mean_packet_loss[i]:.2f}", ha='center', fontsize=10, color='black')
# Adicionar rótulos, título e legendas
plt.xlabel('Network Infrastructure', fontweight='bold')
plt.ylabel('Tasks Loss  (%)', fontweight='bold')
plt.title('Total Tasks Loss ', fontweight='bold')

# Exibir o gráfico
plt.show()


coverage = [79.85, 100, 99.81]

bars = plt.bar(labels, coverage, color=['blue', 'orange', 'green'])
plt.xlabel('Network Infrastructure', fontweight='bold')
plt.ylabel('Coverage (%)', fontweight='bold')
plt.title('Coverage Achieved During Simulation', fontweight='bold')

# Adicionar os valores no topo das barras
for i, bar in enumerate(bars):
    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
             f"{coverage[i]:.2f}%", ha='center', fontsize=10, color='black')

plt.show()