"""Ejecuta cada notebook en un proceso Python limpio, sin sockets Jupyter.

Captura salidas reales IPython y figuras; detiene el proceso ante el primer error.
"""
from pathlib import Path
import base64
import io
import os
import subprocess
import sys
import nbformat

ROOT = Path(__file__).resolve().parents[1]


def execute(name):
    os.chdir(ROOT)
    os.environ['MPLBACKEND'] = 'Agg'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output
    from traitlets.config import Config
    config = Config()
    config.HistoryManager.enabled = False
    config.HistoryManager.hist_file = ':memory:'
    shell = InteractiveShell.instance(config=config)
    path = ROOT/'notebooks'/name
    nb = nbformat.read(path, as_version=4)
    count = 0
    for cell in nb.cells:
        if cell.cell_type != 'code':
            continue
        count += 1
        cell.outputs = []
        cell.execution_count = count
        with capture_output() as captured:
            result = shell.run_cell(cell.source, store_history=True)
        for key in ['stdout', 'stderr']:
            value = getattr(captured, key)
            if value:
                cell.outputs.append(nbformat.v4.new_output('stream', name=key, text=value))
        for output in captured.outputs:
            cell.outputs.append(nbformat.v4.new_output('display_data', data=output.data, metadata=output.metadata))
        if result.error_before_exec or result.error_in_exec:
            nbformat.write(nb, path)
            raise RuntimeError(f'{name}, celda {count}: {result.error_before_exec or result.error_in_exec}')
        for figure_id in plt.get_fignums():
            image = io.BytesIO()
            plt.figure(figure_id).savefig(image, format='png', bbox_inches='tight')
            cell.outputs.append(nbformat.v4.new_output('display_data', data={'image/png': base64.b64encode(image.getvalue()).decode()}))
        plt.close('all')
        print(name, 'celda', count, 'OK', flush=True)
    nbformat.write(nb, path)
    print(name, 'OK: proceso limpio, ejecución secuencial', flush=True)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--execute':
        execute(sys.argv[2])
    else:
        for name in ['01_exploracion.ipynb', '02_modelado.ipynb']:
            subprocess.run([sys.executable, '-u', __file__, '--execute', name], cwd=ROOT,
                           env={**os.environ, 'MPLBACKEND': 'Agg'}, check=True)
