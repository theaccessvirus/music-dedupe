# Ferramenta de Deduplicação de Música

Uma aplicação poderosa e amigável para encontrar e gerenciar arquivos de música duplicados em sua coleção.

## Recursos

- **Detecção inteligente de duplicatas** usando nomes de arquivos e tags ID3
- **Prioridades de formato personalizáveis** para manter seus formatos de áudio preferidos
- **Suporte para arrastar e soltar** para fácil seleção de diretórios
- **Múltiplos métodos de correspondência**:
  - Correspondência baseada em similaridade com limite ajustável
  - Opção de correspondência exata de tamanho para duplicatas perfeitas
  - Correspondência de tags ID3 para resultados mais precisos
- **Opções flexíveis de manipulação**:
  - Mover duplicatas para uma pasta separada
  - Excluir duplicatas para liberar espaço
- **Consciência de qualidade**:
  - Mantém automaticamente a versão de maior qualidade de cada música
  - Considera formato, tamanho do arquivo e taxa de bits nas decisões
- **Painel de instruções integrado**:
  - Ajuda contextual para cada função
  - Explicações detalhadas de cada opção
- **Compatibilidade multiplataforma**:
  - Funciona no macOS (incluindo Apple Silicon)
  - Suporte para Windows
  - Suporte para Linux

## Instalação

### Opção 1: Baixar o Binário Pré-compilado

1. Baixe a versão mais recente para sua plataforma na [página de Lançamentos](https://github.com/username/music-dedupe/releases)
2. macOS: Clique duas vezes no arquivo `.app` para iniciar
3. Windows: Clique duas vezes no arquivo `.exe` para iniciar
4. Linux: Execute o executável a partir do terminal

### Opção 2: Executar a partir do Código-fonte

1. Certifique-se de ter Python 3.6+ instalado
2. Clone este repositório:
   ```
   git clone https://github.com/username/music-dedupe.git
   cd music-dedupe
   ```
3. Instale as dependências necessárias:
   ```
   pip install tkinterdnd2 mutagen
   ```
4. Execute a aplicação:
   ```
   python music_dedupe_gui_pt.py
   ```

### Opção 3: Compilar Seu Próprio Executável

1. Certifique-se de ter Python 3.6+ instalado
2. Clone este repositório:
   ```
   git clone https://github.com/username/music-dedupe.git
   cd music-dedupe
   ```
3. Execute o script de configuração:
   ```
   python setup.py
   ```
4. Encontre o executável no diretório `dist`

## Guia de Uso

### Fluxo de Trabalho Básico

1. **Selecione um diretório de origem** contendo seus arquivos de música
2. **Configure as opções**:
   - Ajuste o limite de similaridade (maior = correspondência mais estrita)
   - Escolha entre mover ou excluir duplicatas
   - Ative/desative o suporte a tags ID3
   - Ative/desative a correspondência exata de tamanho, se necessário
   - Defina as prioridades de formato para manter seus formatos preferidos
3. **Clique em "Escanear Duplicatas"** para analisar sua coleção
4. **Revise os resultados** na área de log
5. **Clique em "Processar Duplicatas"** para mover ou excluir as duplicatas

### Opções Avançadas

#### Limite de Similaridade

- **0.70-0.85**: Correspondência mais agressiva, captura mais duplicatas potenciais, mas pode incluir falsos positivos
- **0.85-0.95**: Correspondência equilibrada, boa para a maioria das coleções
- **0.95-1.00**: Correspondência conservadora, apenas arquivos muito semelhantes serão considerados duplicatas

#### Prioridade de Formato

Defina sua ordem de preferência para formatos de áudio atribuindo valores mais altos (0-10) aos formatos que você prefere manter:

- Valor mais alto = maior prioridade
- O aplicativo manterá o arquivo de maior prioridade quando duplicatas forem encontradas
- Prioridades padrão: FLAC (4), WAV/AIFF/ALAC (3), M4A (2), MP3 (1), WMA (0)

#### Suporte a Tags ID3

Quando ativado, o aplicativo usará metadados de seus arquivos de música para identificar duplicatas, o que geralmente é mais preciso do que usar apenas nomes de arquivos. O aplicativo pode ler tags de:

- Arquivos MP3 (tags ID3)
- Arquivos FLAC (comentários Vorbis)
- Arquivos M4A (metadados iTunes)

#### Correspondência Exata de Tamanho

Quando ativada, apenas arquivos com tamanhos idênticos serão considerados duplicatas. Isso é útil para encontrar duplicatas perfeitas, mas perderá arquivos que foram codificados de maneira diferente.

## Configuração

O aplicativo salva suas configurações em `~/.music_dedupe_config.json`, então você não precisa configurar tudo novamente cada vez que o executar.

## Solução de Problemas

### Problemas Comuns

- **Aplicativo não inicia**: Certifique-se de ter todas as dependências necessárias instaladas
- **Nenhuma duplicata encontrada**: Tente reduzir o limite de similaridade
- **Muitas duplicatas encontradas**: Tente aumentar o limite de similaridade ou ativar a correspondência exata de tamanho
- **Tags ID3 não funcionam**: Instale a biblioteca mutagen (`pip install mutagen`)
- **Arrastar e soltar não funciona**: Instale a biblioteca tkinterdnd2 (`pip install tkinterdnd2`)

### Logs de Erro

Se encontrar problemas, verifique a saída do console para mensagens de erro. Inclua essas informações ao relatar bugs.

## Desenvolvimento

### Compilando a partir do Código-fonte

1. Clone o repositório
2. Instale as dependências de desenvolvimento:
   ```
   pip install tkinterdnd2 mutagen pyinstaller
   ```
3. Execute o script de configuração:
   ```
   python setup.py
   ```

### Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para enviar um Pull Request.

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo LICENSE para detalhes.

## Agradecimentos

- [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) para suporte de arrastar e soltar
- [mutagen](https://mutagen.readthedocs.io/) para manipulação de tags ID3
- [PyInstaller](https://www.pyinstaller.org/) para criação de executáveis