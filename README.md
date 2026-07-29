# 2D Compare

Script em Python para comparar duas versões de desenhos mecânicos 2D.

O programa suporta arquivos PDF, TIFF, TIF, SVG, PNG, JPG, JPEG e BMP. Os desenhos são alinhados manualmente por dois pontos em comum, permitindo corrigir deslocamento, rotação e diferença de escala.

Após o alinhamento, o programa gera arquivos de comparação e abre um visualizador com barra lateral para alternar entre os resultados.

## Funcionalidades

* Leitura de desenhos em PDF, TIFF, TIF, SVG, PNG, JPG, JPEG e BMP.
* Renderização em alta resolução.
* Seleção manual de dois pontos comuns.
* Zoom e movimentação durante a seleção.
* Correção automática de:

  * posição;
  * rotação;
  * escala.
* Comparação colorida entre os desenhos.
* Visualizador com barra lateral.
* Zoom e movimentação sincronizados ao alternar entre as imagens.
* Exportação dos resultados em PNG.

## Cores da comparação

Na visualização `Compare`:

* Preto: geometria presente nos dois desenhos.
* Vermelho: geometria adicionada no desenho novo.
* Azul: geometria removida do desenho novo.
* Branco: área sem geometria.

## Requisitos

* Python 3.10 ou superior.
* Windows, Linux ou macOS.

## Instalação

Abra o PowerShell ou terminal na pasta do projeto e execute:

```powershell
py -m pip install pymupdf pillow resvg-py opencv-python numpy matplotlib
```

Caso o comando `py` não funcione:

```powershell
python -m pip install pymupdf pillow resvg-py opencv-python numpy matplotlib
```

O módulo `tkinter` normalmente já está incluído na instalação do Python para Windows.

## Estrutura da pasta

```text
2d compare/
├── compare_2d.py
├── desenho_antigo.tif
├── desenho_novo.svg
└── README.md
```

## Execução

Dentro da pasta do projeto, execute:

```powershell
py .\compare_2d.py desenho_antigo.tif desenho_novo.svg
```

Para arquivos com espaços no nome:

```powershell
py .\compare_2d.py "desenho antigo.pdf" "desenho novo.svg"
```

O primeiro arquivo é considerado o desenho antigo ou de referência.

O segundo arquivo é considerado o desenho novo ou revisado.

## Seleção dos pontos

O programa abrirá primeiro o desenho antigo.

Use a barra de ferramentas da janela para aplicar zoom ou mover a imagem.

Controles:

* Zoom: ferramenta de lupa.
* Mover imagem: ferramenta de mão.
* Selecionar ponto: `Ctrl + clique esquerdo`.
* Remover último ponto: botão direito.
* Limpar todos os pontos: `Esc`.
* Confirmar seleção: `Enter`.

Selecione exatamente dois pontos.

Depois, o programa abrirá o desenho novo. Selecione os mesmos dois pontos, na mesma ordem.

Exemplo:

```text
Desenho antigo:
P1 = centro do primeiro furo
P2 = centro do segundo furo

Desenho novo:
P1 = centro do mesmo primeiro furo
P2 = centro do mesmo segundo furo
```

Use pontos bem definidos e afastados entre si. Centros de furos, interseções de linhas e vértices são boas referências.

Evite selecionar dois pontos muito próximos, pois pequenos erros de clique podem causar erro significativo de rotação e escala.

## Visualizador

Após o processamento, será aberta a janela `2D Compare`.

A barra lateral permite alternar entre:

1. Desenho antigo.
2. Desenho novo alinhado.
3. Compare.
4. Sobreposição.
5. Diferenças.

Controles do visualizador:

* Scroll do mouse: zoom.
* Arrastar com botão esquerdo: mover imagem.
* Teclas `1` a `5`: alternar visualização.
* Tecla `F`: ajustar imagem à janela.
* Tecla `R`: visualizar em tamanho de pixel 100%.
* Botão `Zoom +`: aumentar zoom.
* Botão `Zoom −`: diminuir zoom.
* Botão `Ajustar à janela`: enquadrar imagem.
* Botão `Zoom 100%`: exibir um pixel da imagem por pixel da tela.

## Arquivos gerados

O programa salva os seguintes arquivos na pasta atual:

```text
01_desenho_antigo.png
02_desenho_novo_alinhado.png
03_sobreposicao.png
04_comparacao_colorida.png
05_diferencas.png
```

### 01_desenho_antigo.png

Desenho antigo colocado no canvas final.

### 02_desenho_novo_alinhado.png

Desenho novo após correção de posição, escala e rotação.

### 03_sobreposicao.png

Sobreposição colorida dos dois desenhos.

### 04_comparacao_colorida.png

Resultado principal da comparação.

### 05_diferencas.png

Máscara contendo somente as regiões consideradas diferentes.

## Configurações principais

As configurações estão no início do arquivo `compare_2d.py`:

```python
MAX_DIMENSION = 16000
PDF_DPI = 600
SVG_MIN_DIMENSION = 12000
COMPARISON_THRESHOLD = 220
TOLERANCE_PIXELS = 2
```

### MAX_DIMENSION

Maior dimensão permitida para uma imagem carregada.

Valor maior melhora a definição, mas aumenta o consumo de memória.

Exemplo mais leve:

```python
MAX_DIMENSION = 8000
```

### PDF_DPI

Resolução usada para renderizar arquivos PDF.

```python
PDF_DPI = 600
```

Valores comuns:

```text
300 DPI = menor consumo de memória
600 DPI = boa qualidade
900 DPI = alta qualidade e alto consumo de memória
```

### SVG_MIN_DIMENSION

Resolução mínima usada para renderizar SVG.

```python
SVG_MIN_DIMENSION = 12000
```

### COMPARISON_THRESHOLD

Limite de intensidade usado para identificar linhas escuras.

```python
COMPARISON_THRESHOLD = 220
```

Valores menores ignoram linhas muito claras.

Valores maiores consideram mais tons de cinza como geometria.

### TOLERANCE_PIXELS

Tolerância usada para considerar linhas próximas como coincidentes.

```python
TOLERANCE_PIXELS = 2
```

Aumente quando os desenhos apresentarem pequenas diferenças de renderização:

```python
TOLERANCE_PIXELS = 3
```

ou:

```python
TOLERANCE_PIXELS = 4
```

Valores muito altos podem ocultar diferenças reais.

## Alinhamento

O alinhamento utiliza uma transformação de similaridade baseada em dois pares de pontos.

Essa transformação corrige:

* translação horizontal;
* translação vertical;
* rotação;
* escala uniforme.

Ela não corrige:

* deformação não uniforme;
* perspectiva;
* distorção do scanner;
* diferença independente de escala nos eixos X e Y.

Para desenhos escaneados com deformação, pode ser necessário usar alinhamento por três ou mais pontos.

## Qualidade da comparação

Para obter melhor resultado:

* use os arquivos originais;
* evite screenshots;
* use pontos de alinhamento precisos;
* escolha pontos afastados;
* prefira centros de furos e interseções;
* mantenha a mesma ordem dos pontos;
* utilize desenhos com a mesma orientação;
* aumente `MAX_DIMENSION` apenas quando houver memória disponível.

## Consumo de memória

Desenhos técnicos em alta resolução podem consumir vários gigabytes de memória durante o alinhamento e a comparação.

Caso apareça erro de memória, reduza:

```python
MAX_DIMENSION = 8000
SVG_MIN_DIMENSION = 6000
PDF_DPI = 300
```

Também verifique se os pontos selecionados estão corretos. Uma escala calculada incorretamente pode gerar um canvas muito grande.

## Problemas comuns

### `pip` não é reconhecido

Use:

```powershell
py -m pip install pymupdf pillow resvg-py opencv-python numpy matplotlib
```

### `py` não é reconhecido

Use:

```powershell
python -m pip install pymupdf pillow resvg-py opencv-python numpy matplotlib
```

### SVG não abre

Reinstale o renderizador:

```powershell
py -m pip install --upgrade resvg-py
```

### TIFF muito grande

Reduza:

```python
MAX_DIMENSION = 8000
```

### Comparação mostra muitas diferenças falsas

Aumente levemente:

```python
TOLERANCE_PIXELS = 3
```

Também confirme se os dois pontos foram selecionados com precisão.

### Imagens borradas

Verifique:

```python
MAX_DIMENSION = 16000
PDF_DPI = 600
SVG_MIN_DIMENSION = 12000
```

Evite ampliar imagens raster de baixa resolução além do tamanho original.

### Janela fecha sem avançar

Selecione exatamente dois pontos usando:

```text
Ctrl + clique esquerdo
```

Depois pressione:

```text
Enter
```

### Zoom seleciona um ponto sem querer

A seleção só ocorre com:

```text
Ctrl + clique esquerdo
```

O clique normal pode ser usado pelas ferramentas de zoom e movimentação.

## Exemplo completo

```powershell
cd "C:\Users\JOALOUR\OneDrive - Daimler Truck\Documentos\VS Code\2d compare"

py -m pip install pymupdf pillow resvg-py opencv-python numpy matplotlib

py .\compare_2d.py desenho_antigo.tif desenho_novo.svg
```

## Limitações

* Apenas a primeira página do PDF ou TIFF é utilizada.
* O alinhamento depende da precisão dos pontos selecionados.
* Arquivos raster muito grandes exigem bastante memória.
* Diferenças de espessura de linha podem aparecer como alterações.
* Fontes ausentes no SVG podem modificar a renderização de textos.
* O programa não interpreta entidades CAD diretamente.
* O resultado é baseado em imagens rasterizadas.

## Licença

Uso interno, acadêmico ou experimental. Adicione uma licença formal ao projeto antes de distribuir publicamente.
