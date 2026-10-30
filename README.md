# Conferência Documental Inteligente

Aplicativo local para importar e conferir simultaneamente de **3 a 20 documentos**, com evidências, localização das divergências e exportação de resultados. Processamento no computador, sem enviar os documentos a um serviço externo de IA.

## Executar

Requer **Python 3.11+**.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra **http://127.0.0.1:8000** e importe 3 a 20 arquivos por clique ou arrastando para a área de importação. Pressione **Conferir documentos** e consulte as evidências. Exporte JSON ou CSV.

**Formatos:** PDF, DOCX, XLSX, CSV, TXT, JPG, PNG. Limite 20 MB por arquivo. OCR de imagens requer instalação de **Tesseract OCR** com idiomas `por` e `eng`. PDF escaneado sem camada de texto exige OCR prévio. A aplicação usa PyMuPDF para PDF, python-docx para Word e openpyxl para planilhas.

**Campos iniciais:** cliente, venda, quadra, lote, loteamento, valor pago, data da venda e ID do cliente. Amplie sinônimos e regras em `app/core.py`.

**Resultados:** correspondente (todos iguais), divergente (valores diferentes), ausente (não extraído em pelo menos um documento), ambíguo (múltiplos valores detectados). Toda correspondência exige identificação de um valor em cada documento. A ausência de extração **não comprova ausência do conteúdo**.

## Testes

```bash
pip install pytest
python -m pytest -q
```

## Limitações e segurança

- A concordância entre documentos não prova a veracidade nem substitui a conferência em fontes oficiais.
- Não é um verificador jurídico de assinaturas, autenticidade ou fraude.
- Layouts complexos, tabelas, textos manuscritos e campos na mesma linha podem exigir adaptações da extração.
- Os arquivos são processados na memória da aplicação; não há persistência configurada. **Não publique documentos reais no repositório.**
- Execute localmente com `--host 127.0.0.1`. Antes de disponibilizar na internet, implemente autenticação, isolamento de processamento, antimalware, limites de acesso e auditoria.
- Limites adicionais: 300 páginas por PDF e 500 mil caracteres extraídos por arquivo.

Licença e distribuição: revisar antes do uso comercial.