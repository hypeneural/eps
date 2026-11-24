# Portal Iso Nunes
## Arquitetura
Python + Jinja2 gera HTML/CSS estático, catálogo JSON, miniaturas JPEG (420x280), imagens de detalhe (até 1400x1000), e ZIP público sanitizado. Nenhum PHP/MySQL/Node no servidor. O GLB original verificado só é carregado quando solicitado. Google model-viewer 4.4.0 via CDN após clique e teste WebGL2; downloads e imagens funcionam sem JS. O framework não entra no PC Windows 7. Tela 1024x600/768, 800x600 e celular são alvos de validação manual.
## Primeiro demo local
```powershell
python -m pip install -r requirements.txt
python scripts/fetch_portal_logo.py
python scripts/gallery_demo.py --output outputs/portal_demo --logo portal_local/logo-isonunes.png
python -m http.server 8000 --bind 127.0.0.1 --directory outputs/portal_demo/site
```
Abrir http://127.0.0.1:8000. Se logo não puder ser recuperada, omitir --logo (wordmark provisório). Não chamar o texto provisório de logo oficial. A demo gera o TP40 nominal de verdade, incluindo GLB e previews, sem CNC. Nenhum DXF é publicado. Abrir em navegador moderno e testar fallback JS desativado. Site público sem login significa arquivos públicos a terceiros; robots não protege.
## Publicação cotidiana
Copiar portal/registry.example.json para portal_local/registry.json (ajustar caminhos relativos ao arquivo). Cada entrada tem id, revision (r01 etc), name, category, source e public_authorized explicitamente verdadeiro somente após conferir que a peça pode ser pública. Uma revisão atual por id. Use caminho de saída novo a cada build:
```powershell
python scripts/build_gallery.py --registry portal_local/registry.json --output outputs/site_r01 --logo portal_local/logo-isonunes.png
python scripts/deploy_gallery.py --site outputs/site_r01
```
O segundo comando sem --execute é dry-run local. A publicação exige senha nova em variáveis de ambiente, não no Git, e raiz remota explícita e dedicada. .env.example é referência, não é carregado automaticamente. FTPS explícito com TLS e certificado verificado, canal de dados protegido. Sem fallback FTP. Confirmar host/porta/pasta/certificado com provedor.
```powershell
$env:EPS_FTP_HOST="eps.etijucas.com.br"
$env:EPS_FTP_USER="eps"
$env:EPS_FTP_REMOTE_ROOT="<raiz confirmada>"
# Definir EPS_FTP_PASSWORD por mecanismo seguro local.
python scripts/deploy_gallery.py --site outputs/site_r01 --initialize --execute
```
--initialize só em raiz dedicada vazia; outras execuções sem --initialize. Verificar HTTPS, downloads, .htaccess (servidor Apache compatível), ausência de listagem, arquivos revogados e MIME. Um único publicador por vez; interromper ao detectar erro. Não modificar raiz remota manualmente; se erro, revisar inventário antes de repetir. Atualização usa inventário anterior, remove arquivos obsoletos, verifica upload por SHA256 via leitura e publica index por último. FTPS/rename e suporte ao .htaccess ainda requerem homologação real. Não usar --execute antes de revisão local.
## Corte
Apenas production_released com pacote íntegro, revalidação do projeto e leitura DXF, e release={"approved":true,"dxf_sha256":"<hash autorizado>"} no registro. PDF opcional exige public_pdf_authorized:true. Nenhum DXF de calibração, draft, G-code, arquivo original ZIP, XML, PST ou macro é publicado. ZIP público recomposto de allowlist. --allow-production é autorização adicional para enviar arquivos de corte ao servidor; não substitui homologação física. Revogar removendo modelo do registro ou substituindo revisão, reconstruir e publicar sem apagar arquivos alheios. Cópias já baixadas não podem ser revogadas. Site atual não mantém histórico visual das revisões retiradas; futuras versões poderão adicionar histórico não executável. Se desenhos forem confidenciais, não publicar sem controle de rede/acesso.
## Segurança operacional
Preferir computador de consulta separado do controlador CNC Windows 7. Não instalar Python ou Blender na fábrica, não abrir navegador durante corte. A galeria não opera a CNC. O operador baixa DXF autorizado e usa LazyCam/Mach3 conforme manual.

## Cadastro simples no Antigravity
```powershell
python scripts/register_gallery_model.py add --id tp40-base-lisa --revision r01 --name "TP40 Base lisa" --category Telhas --source outputs/tp40_review --public-authorized
python scripts/build_gallery.py --registry portal_local/registry.json --output outputs/site_r01
```
A ferramenta de cadastro não habilita produção; exige publicação pública autorizada e revisão crescente. Para retirar: python scripts/register_gallery_model.py remove --id tp40-base-lisa; reconstruir e fazer deploy explicitamente. Os ZIPs são determinísticos para evitar mudança de hash em rebuild idêntico. Logo baixada localmente é detectada automaticamente.

## UX v2
Tema usa a imagem oficial local (fetch_portal_logo.py) e extrai cor dominante saturada, escurecida para contraste mínimo 5:1 sobre branco; verde de corte e âmbar de revisão permanecem semânticos. Textura EPS SVG e ícones SVG locais, sem fontes remotas. Busca por tokens em todos os dados públicos, categorias, somente liberados, lista persistida localmente; sem JS, links continuam disponíveis. Galeria com miniaturas individuais, setas, ampliação, teclado e Escape. Desenho técnico e frontal independentes; seis vistas Cycles + desenho quando presentes nos hashes. GLB núcleo/montagem opcional; fechar remove o elemento WebGL. Não confundir previews compactados de docs com pacote verificado. O relatório CAD 4739fc4 foi integrado sem alterar motor.
