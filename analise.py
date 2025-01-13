import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math

# Dados para os dois cenários
labels = ['Scenario 1', 'Scenario 2']
mean_jitter = [9.97, 9.93]
max_jitter = [14.98, 26.46]
min_jitter = [7.34, 7.00]

# Calcular a variabilidade (erro) com base na diferença entre máximo e mínimo
error_upper = [max_val - mean_val for max_val, mean_val in zip(max_jitter, mean_jitter)]  # Máximo - Médio
error_lower = [mean_val - min_val for mean_val, min_val in zip(mean_jitter, min_jitter)]  # Médio - Mínimo

# Criar o gráfico de barras com barras de erro
plt.bar(labels, mean_jitter, color=['blue', 'orange'], yerr=[error_lower, error_upper], capsize=5, label='Jitter Médio')

# Adicionar rótulos, título e legendas
plt.xlabel('Scenario', fontweight='bold')
plt.ylabel('Jitter (ms)', fontweight='bold')
plt.title('Average Jitter', fontweight='bold')


# Exibir o gráfico
plt.show()


# Dados para os dois cenários
labels = ['Scenario 1', 'Scenario 2']
mean_jitter = [23.99, 43.59]
max_jitter = [64, 122]
min_jitter = [10, 10]

# Calcular a variabilidade (erro) com base na diferença entre máximo e mínimo
error_upper = [max_val - mean_val for max_val, mean_val in zip(max_jitter, mean_jitter)]  # Máximo - Médio
error_lower = [mean_val - min_val for mean_val, min_val in zip(mean_jitter, min_jitter)]  # Médio - Mínimo

# Criar o gráfico de barras com barras de erro
plt.bar(labels, mean_jitter, color=['blue', 'orange'], yerr=[error_lower, error_upper], capsize=5, label='Average ETE Latency')

# Adicionar rótulos, título e legendas
plt.xlabel('Scenario', fontweight='bold')
plt.ylabel('Latency (ms)', fontweight='bold')
plt.title('Average ETE Latency', fontweight='bold')


# Exibir o gráfico
plt.show()

# Dados para os dois cenários
scenarios = ['Scenario 1', 'Scenario 2']
packet_loss = [15, 17]
coverage = [72.45, 99.15]

# Gráfico de Packet Loss
plt.figure(figsize=(10, 5))

bars = plt.bar(scenarios, packet_loss, color=['blue', 'orange'], alpha=0.8)
plt.xlabel('Scenario', fontweight='bold')
plt.ylabel('Packet Loss (%)', fontweight='bold')
plt.title('Total Packet Loss', fontweight='bold')

# Adicionar os valores no topo das barras
for i, bar in enumerate(bars):
    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
             f"{packet_loss[i]:.2f}", ha='center', fontsize=10, color='black')

plt.show()

# Gráfico de Coverage
plt.figure(figsize=(10, 5))

bars = plt.bar(scenarios, coverage, color=['green', 'purple'], alpha=0.8)
plt.xlabel('Scenario', fontweight='bold')
plt.ylabel('Coverage (%)', fontweight='bold')
plt.title('Coverage Achieved During Simulation', fontweight='bold')

# Adicionar os valores no topo das barras
for i, bar in enumerate(bars):
    plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
             f"{coverage[i]:.2f}%", ha='center', fontsize=10, color='black')

plt.show()



# Carregar os dados do CSV (substitua 'arquivo.csv' pelo nome do seu arquivo)
data = pd.read_csv("results/sim_trace_link.csv")

data = data.sort_values(by='ctime').drop_duplicates(subset='id', keep='first')
# Criar uma nova coluna com os tempos de recepção agrupados por intervalos de 60000
data['group'] = (data['ctime'] // 60000).astype(int)

# Contar o número de IDs em cada grupo
grouped_ids = data.groupby('group').size()

simulation_time = 600000 // 60000  # Número total de grupos
all_groups = pd.Series(0, index=range(simulation_time))
grouped_ids = grouped_ids.reindex(all_groups.index, fill_value=0)


# Função para calcular o número de IDs esperados em cada grupo
def calculate_expected_ids(group_number):
    if group_number == 0:
        return max(0, math.floor((60000 - 910) / 50))
    else:
        return math.floor(60000 / 50)

# Calcular o número de IDs esperados para cada grupo
expected_ids = grouped_ids.index.map(calculate_expected_ids)

# Calcular o percentual de tarefas perdidas
lost_tasks_percentage = (1 - (grouped_ids / expected_ids)) * 100

# Substituir NaN por 0 (ocorre quando expected_ids é 0)
lost_tasks_percentage = lost_tasks_percentage.fillna(0)

# Plotar o gráfico
plt.figure(figsize=(10, 6))
plt.plot(grouped_ids.index, lost_tasks_percentage, marker='o', label='Percentual de Tarefas Perdidas')
plt.title('Percentual de Tarefas Perdidas por Tempo de Simulação')
plt.xlabel('Grupo de Tempo (Intervalos de 60000)')
plt.ylabel('Percentual de Tarefas Perdidas (%)')
plt.grid(True)
plt.legend()
plt.show()


# Carregar os dados do CSV (substitua 'arquivo.csv' pelo nome do seu arquivo)
data = pd.read_csv("results/sim_trace.csv")

# Calcular a latência individual (time_reception - time_emit)
data['latency'] = data['time_reception'] - data['time_emit']

# Guardar o primeiro time_emit por tarefa (id)
time_emit_per_task = data.groupby('id')['time_emit'].first().reset_index()
time_emit_per_task.rename(columns={'time_emit': 'first_time_emit'}, inplace=True)
print(time_emit_per_task)
# Combinar a latência total por tarefa com o primeiro time_emit
latency_per_task = data.groupby('id')['latency'].sum().reset_index()
latency_per_task = latency_per_task.merge(time_emit_per_task, on='id')

# Criar uma coluna para o grupo baseado no primeiro time_emit
latency_per_task['group'] = (latency_per_task['first_time_emit'] // 60000).astype(int)
print(latency_per_task)
# Calcular a latência média por grupo
latency_per_group = latency_per_task.groupby('group')['latency'].mean()

# Adicionar grupos faltantes até o tempo total de simulação (simulation_time)
simulation_time = 600000 // 60000  # Número total de grupos
all_groups = pd.Series(0, index=range(simulation_time))
latency_per_group = latency_per_group.reindex(all_groups.index, fill_value=None)

# Plotar o gráfico de latência média end-to-end
plt.figure(figsize=(10, 6))
plt.plot(latency_per_group.index, latency_per_group, marker='o', color='orange', label='Latência Média End-to-End')
plt.title('Latência Média End-to-End por Tempo de Simulação')
plt.xlabel('Grupo de Tempo (Intervalos de 60000)')
plt.ylabel('Latência Média End-to-End (ms)')
plt.grid(True)
plt.legend()
plt.show()

