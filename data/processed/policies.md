<!--
Curated transcription of data/raw/store_policies.pdf (Manual de Políticas e Procedimentos v2.1, June 2025).
PDF text extraction was too noisy, so the manual was transcribed by hand and split into sections.
Each "## <key> | <title>" heading becomes one entry of the get_store_policy tool.

Curation notes (ambiguities in the source, resolved and documented in the README):
- E-mail appears as "contato@empóriodamusica.com.br" (with accent) on page 2; the cover-page spelling
  without accent is used, since domains with accents are almost certainly a typo.
- Phone: page 2 lists (67) 3341-4444 as "Telefone / WhatsApp", section 7 lists WhatsApp as (67) 3321-4500.
  Both are kept: 3341-4444 as the store phone, 3321-4500 as the WhatsApp channel (section 7 is the more specific one).
- Installments: the payment table says "minimum installment R$ 100,00" while section 3.1 defines tiers.
  Section 3.1 (more detailed) prevails; the table value is read as the 7x–12x tier.
  "até 3x sem valor mínimo (exceto abaixo de R$ 50,00)" is read as: 1x–3x with minimum installment of R$ 50,00.
- Section 7 (service guidelines) is not exposed as a tool: it is encoded in the agent's system prompt.
-->

## loja | Sobre a loja, endereço e contato

A Empório da Música é uma loja especializada em instrumentos musicais, fundada em 2008 em Campo Grande, Mato Grosso do Sul. Com mais de 15 anos de atuação, é referência regional na venda de instrumentos para músicos iniciantes, intermediários e profissionais.

O catálogo abrange instrumentos de marcas nacionais e internacionais, incluindo guitarras, baixos, violões, baterias, teclados, instrumentos de sopro, cordas orquestrais e ukuleles. A loja trabalha **exclusivamente com instrumentos musicais** — não comercializa acessórios como cordas, palhetas, cabos, cases, pedais ou amplificadores.

Missão: democratizar o acesso a instrumentos musicais de qualidade na região Centro-Oeste, com atendimento especializado e preços competitivos.

| Campo | Informação |
|---|---|
| Razão Social | Empório da Música Instrumentos Musicais Ltda. |
| Nome Fantasia | Empório da Música |
| CNPJ | 12.345.678/0001-90 |
| Endereço | Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, CEP 79202-333 |
| Telefone | (67) 3341-4444 |
| WhatsApp | (67) 3321-4500 |
| E-mail | contato@emporiodamusica.com.br |
| Fundação | 2008 |

## horario | Horário de funcionamento

O atendimento presencial na loja e o atendimento via WhatsApp seguem o mesmo horário (fora do expediente, o WhatsApp tem respostas automáticas).

| Dia | Horário |
|---|---|
| Segunda a Sexta-feira | 09:00 às 18:00 |
| Sábado | 09:00 às 13:00 |
| Domingo e Feriados | Fechado |

Em datas especiais (Black Friday, Aniversário da Loja, Natal) o horário pode ser estendido. Alterações são comunicadas com antecedência nas redes sociais e no WhatsApp.

## pagamento | Formas de pagamento e parcelamento

Formas aceitas para compras presenciais e online:

| Forma | Condições | Observações |
|---|---|---|
| PIX | À vista | 5% de desconto sobre o preço de tabela (não se aplica a preços já promocionais) |
| Cartão de Débito | À vista | Todas as bandeiras |
| Cartão de Crédito | Até 12x sem juros | Ver regras de parcelamento |
| Boleto Bancário | À vista | Compensação em até 3 dias úteis |

Regras de parcelamento (todas sem juros):
- 1x a 3x: parcela mínima de R$ 50,00.
- 4x a 6x: parcela mínima de R$ 80,00.
- 7x a 12x: parcela mínima de R$ 100,00.
- Combinação de formas de pagamento (ex.: PIX + cartão) é permitida para compras acima de R$ 2.000,00.

## trocas_devolucoes | Trocas e devoluções

A loja segue o Código de Defesa do Consumidor (Lei nº 8.078/90).

Direito de arrependimento (compras online):
- Devolução em até 7 (sete) dias corridos após o recebimento do produto, sem necessidade de justificativa.
- Produto na embalagem original, sem sinais de uso, com todos os acessórios e manuais.
- Reembolso na mesma forma de pagamento original em até 10 dias úteis.
- Frete de devolução por conta da loja.

Trocas por defeito:
- Produtos com defeito de fabricação podem ser trocados em até 30 (trinta) dias corridos após a compra.
- Após 30 dias, o cliente deve acionar a garantia diretamente com o fabricante; a loja pode intermediar mediante solicitação.
- Danos por mau uso, quedas, umidade excessiva ou modificações não autorizadas não são cobertos.

Trocas por preferência (cor, modelo, tamanho):
- Permitidas em até 7 dias, mediante disponibilidade do produto desejado.
- Produto em perfeito estado e na embalagem original.
- Diferenças de valor são cobradas ou reembolsadas conforme o caso.

Itens não elegíveis para troca:
- Instrumentos com personalização ou ajustes sob encomenda (setup, regulagem especial).
- Produtos de liquidação com aviso explícito de "venda final".
- Boquilhas de instrumentos de sopro, por questões de higiene.

## frete | Frete, entregas e rastreamento

Região metropolitana de Campo Grande:
- Frete grátis para pedidos acima de R$ 500,00; abaixo disso, taxa fixa de R$ 35,00.
- Prazo de 1 a 3 dias úteis, entrega por motoboy próprio (o cliente é contactado por telefone antes).

Outras cidades (Correios e Jadlog):

| Modalidade | Prazo estimado | Rastreamento | Seguro |
|---|---|---|---|
| PAC (Correios) | 5 a 12 dias úteis | Sim | Incluído |
| SEDEX (Correios) | 2 a 5 dias úteis | Sim | Incluído |
| Jadlog (.package) | 3 a 8 dias úteis | Sim | Incluído |

O frete é calculado com base no CEP de destino, peso e dimensões. Instrumentos de grande porte (baterias acústicas, pianos digitais, contrabaixos) podem exigir frete especial com cotação individual. Todos os envios têm seguro contra extravio e danos; em caso de avaria, o cliente deve recusar o recebimento e contatar a loja imediatamente.

Rastreamento: o código é enviado por e-mail e WhatsApp quando o pedido é despachado. Formato: BR + 9 caracteres alfanuméricos + BR (ex.: BR4K7M2X9P1BR). Pode ser consultado no site dos Correios ou da Jadlog.

## promocoes | Promoções e descontos

Campanhas periódicas:
- Aniversário da Loja (agosto): 10% a 25% em itens selecionados.
- Black Friday (novembro): 15% a 30% em todo o catálogo.
- Volta às Aulas (fevereiro): descontos para estudantes.
- Queima de Estoque: promoções pontuais.
- Semana do Músico: semana do Dia do Músico (22 de novembro).

Regras:
- Promoções não são cumulativas. O desconto de PIX (5%) não se aplica sobre preços já promocionais.
- Promoções sujeitas à disponibilidade de estoque; produtos esgotados não geram direito a reserva de preço (rain check).
- Preços promocionais são sempre apresentados junto ao preço original e ao percentual de desconto.
- Só vale o que está ativo no sistema: uma campanha do calendário só existe para o cliente quando houver promoção ativa cadastrada.

## garantia | Garantia

- Garantia legal (CDC): 90 (noventa) dias contra defeitos de fabricação, contados do recebimento.
- Garantia do fabricante: varia de 6 meses a 2 anos, conforme o certificado que acompanha o produto.

A garantia não cobre:
- Desgaste natural de peças (trastes, cordas, feltros, palhetas de sopro).
- Danos por mau uso, queda ou exposição a condições climáticas extremas.
- Modificações ou reparos feitos por terceiros não autorizados.
- Danos estéticos que não afetem a funcionalidade.

## privacidade | Privacidade e proteção de dados (LGPD)

A loja segue a LGPD (Lei nº 13.709/2018). Dados pessoais (nome, telefone, e-mail, endereço) são usados exclusivamente para: processamento e entrega de pedidos; comunicação sobre status e rastreamento; envio de promoções (com consentimento explícito); obrigações legais e fiscais.

Dados de clientes não são compartilhados com terceiros para marketing. O cliente pode solicitar a exclusão dos seus dados a qualquer momento pelo WhatsApp ou e-mail.
