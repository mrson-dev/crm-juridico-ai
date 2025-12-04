#!/bin/bash

#===============================================================================
#
#   CRM JURÍDICO AI - Git Helper
#   
#   Script para automatizar operações Git comuns no projeto.
#   Simplifica commit, push, pull, branches e mais.
#
#   Uso: ./scripts/git-helper.sh [comando] [argumentos]
#
#===============================================================================

set -e

#-------------------------------------------------------------------------------
# CORES E FORMATAÇÃO
#-------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

#-------------------------------------------------------------------------------
# VARIÁVEIS
#-------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
REMOTE_NAME="origin"

#-------------------------------------------------------------------------------
# FUNÇÕES DE UI
#-------------------------------------------------------------------------------

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           🔀 CRM Jurídico - Git Helper                        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

confirm() {
    local message="$1"
    local default="${2:-n}"
    
    if [ "$default" = "y" ]; then
        read -p "$(echo -e "${YELLOW}?${NC} $message [Y/n]: ")" response
        response=${response:-y}
    else
        read -p "$(echo -e "${YELLOW}?${NC} $message [y/N]: ")" response
        response=${response:-n}
    fi
    
    [[ "$response" =~ ^[Yy]$ ]]
}

#-------------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
#-------------------------------------------------------------------------------

check_git_repo() {
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        print_error "Não está em um repositório Git!"
        exit 1
    fi
}

get_changed_files() {
    git status --porcelain | wc -l | tr -d ' '
}

get_staged_files() {
    git diff --cached --name-only | wc -l | tr -d ' '
}

get_commit_count_ahead() {
    git rev-list --count ${REMOTE_NAME}/${CURRENT_BRANCH}..HEAD 2>/dev/null || echo "0"
}

get_commit_count_behind() {
    git rev-list --count HEAD..${REMOTE_NAME}/${CURRENT_BRANCH} 2>/dev/null || echo "0"
}

#-------------------------------------------------------------------------------
# COMANDO: status
#-------------------------------------------------------------------------------
cmd_status() {
    print_banner
    echo -e "${WHITE}📊 Status do Repositório${NC}"
    echo ""
    
    # Branch atual
    echo -e "  ${DIM}Branch:${NC}     ${GREEN}$CURRENT_BRANCH${NC}"
    
    # Remote
    local remote_url=$(git remote get-url $REMOTE_NAME 2>/dev/null || echo "não configurado")
    echo -e "  ${DIM}Remote:${NC}     $remote_url"
    
    # Fetch para atualizar informações
    git fetch $REMOTE_NAME --quiet 2>/dev/null || true
    
    # Commits ahead/behind
    local ahead=$(get_commit_count_ahead)
    local behind=$(get_commit_count_behind)
    
    if [ "$ahead" -gt 0 ] && [ "$behind" -gt 0 ]; then
        echo -e "  ${DIM}Sync:${NC}       ${YELLOW}↑$ahead ↓$behind (divergiu)${NC}"
    elif [ "$ahead" -gt 0 ]; then
        echo -e "  ${DIM}Sync:${NC}       ${GREEN}↑$ahead commits para push${NC}"
    elif [ "$behind" -gt 0 ]; then
        echo -e "  ${DIM}Sync:${NC}       ${YELLOW}↓$behind commits para pull${NC}"
    else
        echo -e "  ${DIM}Sync:${NC}       ${GREEN}✓ Sincronizado${NC}"
    fi
    
    echo ""
    echo -e "${WHITE}📁 Arquivos${NC}"
    
    local changed=$(get_changed_files)
    local staged=$(get_staged_files)
    
    if [ "$changed" -eq 0 ]; then
        echo -e "  ${GREEN}✓ Working directory limpo${NC}"
    else
        echo -e "  ${DIM}Modificados:${NC} $changed arquivo(s)"
        echo -e "  ${DIM}Staged:${NC}      $staged arquivo(s)"
        echo ""
        
        # Mostrar arquivos modificados
        echo -e "${DIM}  Mudanças:${NC}"
        git status --short | head -20 | while read line; do
            local status="${line:0:2}"
            local file="${line:3}"
            case "$status" in
                "M "*)  echo -e "    ${GREEN}M${NC}  $file" ;;  # Modified, staged
                " M"*)  echo -e "    ${YELLOW}M${NC}  $file" ;;  # Modified, not staged
                "A "*)  echo -e "    ${GREEN}A${NC}  $file" ;;  # Added
                "D "*)  echo -e "    ${RED}D${NC}  $file" ;;    # Deleted
                "??"*)  echo -e "    ${PURPLE}?${NC}  $file" ;;  # Untracked
                *)      echo -e "    $status $file" ;;
            esac
        done
        
        local total_changed=$(get_changed_files)
        if [ "$total_changed" -gt 20 ]; then
            echo -e "    ${DIM}... e mais $((total_changed - 20)) arquivo(s)${NC}"
        fi
    fi
    
    echo ""
}

#-------------------------------------------------------------------------------
# COMANDO: save (add + commit)
#-------------------------------------------------------------------------------
cmd_save() {
    local message="$1"
    local push_after="${2:-false}"
    
    print_banner
    
    local changed=$(get_changed_files)
    if [ "$changed" -eq 0 ]; then
        print_warning "Nenhuma alteração para salvar"
        exit 0
    fi
    
    # Se não passou mensagem, abre editor ou pede input
    if [ -z "$message" ]; then
        echo -e "${WHITE}📝 Mudanças a serem commitadas:${NC}"
        echo ""
        git status --short
        echo ""
        
        # Sugerir mensagem baseada nos arquivos
        local suggestion=""
        if git status --short | grep -q "^A"; then
            suggestion="feat: "
        elif git status --short | grep -q "^M"; then
            suggestion="fix: "
        elif git status --short | grep -q "^D"; then
            suggestion="chore: "
        fi
        
        read -p "$(echo -e "${YELLOW}?${NC} Mensagem do commit [$suggestion]: ")" message
        message="${message:-$suggestion}"
        
        if [ -z "$message" ]; then
            print_error "Mensagem é obrigatória"
            exit 1
        fi
    fi
    
    # Add all
    print_step "Adicionando arquivos..."
    git add -A
    print_success "Arquivos adicionados"
    
    # Commit
    print_step "Criando commit..."
    git commit -m "$message"
    print_success "Commit criado: $message"
    
    # Push opcional
    if [ "$push_after" = "true" ] || [ "$push_after" = "-p" ]; then
        cmd_push
    else
        echo ""
        local ahead=$(get_commit_count_ahead)
        if [ "$ahead" -gt 0 ]; then
            print_info "Use '${BOLD}./scripts/git-helper.sh push${NC}' para enviar $ahead commit(s)"
        fi
    fi
}

#-------------------------------------------------------------------------------
# COMANDO: push
#-------------------------------------------------------------------------------
cmd_push() {
    print_banner
    
    local ahead=$(get_commit_count_ahead)
    if [ "$ahead" -eq 0 ]; then
        print_info "Nenhum commit para push"
        return 0
    fi
    
    print_step "Enviando $ahead commit(s) para $REMOTE_NAME/$CURRENT_BRANCH..."
    
    if git push $REMOTE_NAME $CURRENT_BRANCH; then
        print_success "Push realizado com sucesso!"
        
        # Mostrar URL do repo se for GitHub
        local remote_url=$(git remote get-url $REMOTE_NAME 2>/dev/null)
        if [[ "$remote_url" == *"github.com"* ]]; then
            local repo_url=$(echo "$remote_url" | sed 's/\.git$//' | sed 's/git@github.com:/https:\/\/github.com\//')
            echo ""
            print_info "Ver no GitHub: $repo_url"
        fi
    else
        print_error "Falha no push"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# COMANDO: pull
#-------------------------------------------------------------------------------
cmd_pull() {
    print_banner
    
    print_step "Buscando atualizações de $REMOTE_NAME/$CURRENT_BRANCH..."
    git fetch $REMOTE_NAME
    
    local behind=$(get_commit_count_behind)
    if [ "$behind" -eq 0 ]; then
        print_success "Já está atualizado!"
        return 0
    fi
    
    print_step "Aplicando $behind commit(s)..."
    
    if git pull $REMOTE_NAME $CURRENT_BRANCH; then
        print_success "Pull realizado com sucesso!"
    else
        print_error "Conflitos detectados! Resolva manualmente."
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# COMANDO: sync (pull + push)
#-------------------------------------------------------------------------------
cmd_sync() {
    print_banner
    
    local changed=$(get_changed_files)
    if [ "$changed" -gt 0 ]; then
        print_warning "Existem mudanças não commitadas!"
        git status --short | head -5
        echo ""
        
        if confirm "Deseja fazer stash das mudanças?"; then
            git stash push -m "Auto-stash before sync"
            print_success "Mudanças guardadas em stash"
        else
            print_error "Commite ou stash suas mudanças primeiro"
            exit 1
        fi
    fi
    
    # Pull primeiro
    print_step "Sincronizando com remote..."
    git fetch $REMOTE_NAME
    
    local behind=$(get_commit_count_behind)
    if [ "$behind" -gt 0 ]; then
        print_step "Puxando $behind commit(s)..."
        git pull $REMOTE_NAME $CURRENT_BRANCH --rebase
    fi
    
    # Depois push
    local ahead=$(get_commit_count_ahead)
    if [ "$ahead" -gt 0 ]; then
        print_step "Enviando $ahead commit(s)..."
        git push $REMOTE_NAME $CURRENT_BRANCH
    fi
    
    print_success "Sincronizado com sucesso!"
    
    # Restaurar stash se existir
    if git stash list | grep -q "Auto-stash before sync"; then
        if confirm "Restaurar mudanças do stash?"; then
            git stash pop
            print_success "Mudanças restauradas"
        fi
    fi
}

#-------------------------------------------------------------------------------
# COMANDO: branch
#-------------------------------------------------------------------------------
cmd_branch() {
    local action="${1:-list}"
    local branch_name="$2"
    
    print_banner
    
    case "$action" in
        list|ls)
            echo -e "${WHITE}📋 Branches${NC}"
            echo ""
            git branch -a --format='%(HEAD) %(refname:short) %(color:dim)%(committerdate:relative)%(color:reset)' | head -20
            ;;
        
        new|create)
            if [ -z "$branch_name" ]; then
                read -p "$(echo -e "${YELLOW}?${NC} Nome da nova branch: ")" branch_name
            fi
            
            if [ -z "$branch_name" ]; then
                print_error "Nome da branch é obrigatório"
                exit 1
            fi
            
            print_step "Criando branch '$branch_name'..."
            git checkout -b "$branch_name"
            print_success "Branch criada e checkout feito!"
            ;;
        
        delete|del|rm)
            if [ -z "$branch_name" ]; then
                read -p "$(echo -e "${YELLOW}?${NC} Nome da branch para deletar: ")" branch_name
            fi
            
            if [ "$branch_name" = "main" ] || [ "$branch_name" = "master" ]; then
                print_error "Não é possível deletar a branch principal!"
                exit 1
            fi
            
            if confirm "Deletar branch '$branch_name'?"; then
                git branch -d "$branch_name" 2>/dev/null || git branch -D "$branch_name"
                print_success "Branch deletada"
            fi
            ;;
        
        switch|checkout|co)
            if [ -z "$branch_name" ]; then
                echo -e "${WHITE}Branches disponíveis:${NC}"
                git branch --format='%(refname:short)' | nl
                echo ""
                read -p "$(echo -e "${YELLOW}?${NC} Número ou nome da branch: ")" branch_name
            fi
            
            # Se for número, pegar o nome
            if [[ "$branch_name" =~ ^[0-9]+$ ]]; then
                branch_name=$(git branch --format='%(refname:short)' | sed -n "${branch_name}p")
            fi
            
            print_step "Mudando para '$branch_name'..."
            git checkout "$branch_name"
            print_success "Agora em: $branch_name"
            ;;
        
        *)
            print_error "Ação desconhecida: $action"
            echo "Uso: branch [list|new|delete|switch] [nome]"
            exit 1
            ;;
    esac
}

#-------------------------------------------------------------------------------
# COMANDO: log
#-------------------------------------------------------------------------------
cmd_log() {
    local count="${1:-10}"
    
    print_banner
    echo -e "${WHITE}📜 Últimos $count commits${NC}"
    echo ""
    
    git log --oneline --graph --decorate -n "$count" --format="%C(auto)%h%C(reset) %C(dim)%ar%C(reset) %s %C(cyan)<%an>%C(reset)"
}

#-------------------------------------------------------------------------------
# COMANDO: undo
#-------------------------------------------------------------------------------
cmd_undo() {
    local action="${1:-help}"
    
    print_banner
    
    case "$action" in
        commit)
            if confirm "Desfazer último commit (mantendo arquivos)?"; then
                git reset --soft HEAD~1
                print_success "Commit desfeito. Arquivos mantidos staged."
            fi
            ;;
        
        staged|stage)
            if confirm "Remover todos os arquivos do stage?"; then
                git reset HEAD
                print_success "Arquivos removidos do stage"
            fi
            ;;
        
        changes|modified)
            print_warning "Isso irá PERDER todas as mudanças não commitadas!"
            if confirm "Tem certeza?"; then
                git checkout -- .
                git clean -fd
                print_success "Mudanças descartadas"
            fi
            ;;
        
        *)
            echo -e "${WHITE}Opções de undo:${NC}"
            echo ""
            echo "  ${CYAN}commit${NC}   - Desfaz último commit (mantém arquivos)"
            echo "  ${CYAN}staged${NC}   - Remove arquivos do stage"
            echo "  ${CYAN}changes${NC}  - Descarta todas as mudanças não commitadas"
            echo ""
            echo "Uso: undo [commit|staged|changes]"
            ;;
    esac
}

#-------------------------------------------------------------------------------
# COMANDO: stash
#-------------------------------------------------------------------------------
cmd_stash() {
    local action="${1:-save}"
    local message="$2"
    
    print_banner
    
    case "$action" in
        save|push)
            local changed=$(get_changed_files)
            if [ "$changed" -eq 0 ]; then
                print_warning "Nenhuma mudança para guardar"
                exit 0
            fi
            
            if [ -z "$message" ]; then
                message="WIP: $(date '+%Y-%m-%d %H:%M')"
            fi
            
            git stash push -m "$message"
            print_success "Mudanças guardadas: $message"
            ;;
        
        pop|apply)
            if ! git stash list | grep -q .; then
                print_warning "Nenhum stash para restaurar"
                exit 0
            fi
            
            git stash pop
            print_success "Mudanças restauradas"
            ;;
        
        list|ls)
            echo -e "${WHITE}📦 Stashes salvos${NC}"
            echo ""
            if git stash list | grep -q .; then
                git stash list
            else
                print_info "Nenhum stash salvo"
            fi
            ;;
        
        drop|clear)
            if confirm "Limpar todos os stashes?"; then
                git stash clear
                print_success "Stashes removidos"
            fi
            ;;
        
        *)
            echo "Uso: stash [save|pop|list|drop] [mensagem]"
            ;;
    esac
}

#-------------------------------------------------------------------------------
# COMANDO: release
#-------------------------------------------------------------------------------
cmd_release() {
    local version="$1"
    
    print_banner
    
    if [ -z "$version" ]; then
        # Sugerir próxima versão
        local last_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
        local major=$(echo "$last_tag" | sed 's/v//' | cut -d. -f1)
        local minor=$(echo "$last_tag" | sed 's/v//' | cut -d. -f2)
        local patch=$(echo "$last_tag" | sed 's/v//' | cut -d. -f3)
        
        echo -e "${WHITE}Última versão:${NC} $last_tag"
        echo ""
        echo "  1) v$major.$minor.$((patch + 1)) (patch)"
        echo "  2) v$major.$((minor + 1)).0 (minor)"
        echo "  3) v$((major + 1)).0.0 (major)"
        echo "  4) Versão customizada"
        echo ""
        
        read -p "$(echo -e "${YELLOW}?${NC} Escolha [1-4]: ")" choice
        
        case "$choice" in
            1) version="v$major.$minor.$((patch + 1))" ;;
            2) version="v$major.$((minor + 1)).0" ;;
            3) version="v$((major + 1)).0.0" ;;
            4) read -p "Versão (ex: v1.0.0): " version ;;
            *) print_error "Opção inválida"; exit 1 ;;
        esac
    fi
    
    # Validar formato
    if [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Formato inválido. Use: vX.Y.Z"
        exit 1
    fi
    
    # Verificar se tag já existe
    if git tag | grep -q "^$version$"; then
        print_error "Tag $version já existe!"
        exit 1
    fi
    
    # Confirmar
    echo ""
    echo -e "${WHITE}Release:${NC} $version"
    echo -e "${DIM}Branch:${NC}  $CURRENT_BRANCH"
    echo ""
    
    if ! confirm "Criar release $version?"; then
        exit 0
    fi
    
    # Criar tag
    print_step "Criando tag $version..."
    git tag -a "$version" -m "Release $version"
    print_success "Tag criada"
    
    # Push tag
    print_step "Enviando tag..."
    git push $REMOTE_NAME "$version"
    print_success "Tag enviada!"
    
    # Mostrar URL do release se for GitHub
    local remote_url=$(git remote get-url $REMOTE_NAME 2>/dev/null)
    if [[ "$remote_url" == *"github.com"* ]]; then
        local repo_url=$(echo "$remote_url" | sed 's/\.git$//' | sed 's/git@github.com:/https:\/\/github.com\//')
        echo ""
        print_info "Criar release: $repo_url/releases/new?tag=$version"
    fi
}

#-------------------------------------------------------------------------------
# COMANDO: quick (commit + push rápido)
#-------------------------------------------------------------------------------
cmd_quick() {
    local message="$1"
    
    if [ -z "$message" ]; then
        # Auto-gerar mensagem baseada nos arquivos
        local files=$(git status --short | head -3 | awk '{print $2}' | xargs | tr ' ' ', ')
        message="update: $files"
    fi
    
    print_banner
    print_step "Quick commit & push..."
    
    git add -A
    git commit -m "$message"
    git push $REMOTE_NAME $CURRENT_BRANCH
    
    print_success "Feito! Commit: $message"
}

#-------------------------------------------------------------------------------
# COMANDO: clean
#-------------------------------------------------------------------------------
cmd_clean() {
    print_banner
    
    echo -e "${WHITE}🧹 Limpeza do Repositório${NC}"
    echo ""
    
    # Branches merged
    local merged=$(git branch --merged | grep -v "\*" | grep -v "main" | grep -v "master" | wc -l | tr -d ' ')
    if [ "$merged" -gt 0 ]; then
        echo -e "Branches merged para deletar: ${YELLOW}$merged${NC}"
        git branch --merged | grep -v "\*" | grep -v "main" | grep -v "master" | while read branch; do
            echo "  - $branch"
        done
        
        if confirm "Deletar branches merged?"; then
            git branch --merged | grep -v "\*" | grep -v "main" | grep -v "master" | xargs -r git branch -d
            print_success "Branches removidas"
        fi
    else
        print_success "Nenhuma branch merged para limpar"
    fi
    
    echo ""
    
    # Arquivos não rastreados
    local untracked=$(git clean -n -d | wc -l | tr -d ' ')
    if [ "$untracked" -gt 0 ]; then
        echo -e "Arquivos não rastreados: ${YELLOW}$untracked${NC}"
        git clean -n -d | head -10
        
        if confirm "Remover arquivos não rastreados?"; then
            git clean -fd
            print_success "Arquivos removidos"
        fi
    else
        print_success "Nenhum arquivo não rastreado"
    fi
    
    echo ""
    
    # GC
    if confirm "Executar garbage collection?"; then
        print_step "Otimizando repositório..."
        git gc --prune=now
        print_success "Repositório otimizado"
    fi
}

#-------------------------------------------------------------------------------
# HELP
#-------------------------------------------------------------------------------
show_help() {
    print_banner
    echo -e "${WHITE}Comandos disponíveis:${NC}"
    echo ""
    echo -e "  ${CYAN}status${NC}              Mostra status detalhado do repositório"
    echo -e "  ${CYAN}save${NC} [msg] [-p]    Adiciona e commita (${DIM}-p para push${NC})"
    echo -e "  ${CYAN}quick${NC} [msg]        Commit rápido + push automático"
    echo -e "  ${CYAN}push${NC}               Envia commits para o remote"
    echo -e "  ${CYAN}pull${NC}               Baixa atualizações do remote"
    echo -e "  ${CYAN}sync${NC}               Pull + push (sincroniza tudo)"
    echo ""
    echo -e "  ${CYAN}branch${NC} [ação]      Gerencia branches"
    echo -e "    ${DIM}list${NC}              Lista branches"
    echo -e "    ${DIM}new <nome>${NC}        Cria nova branch"
    echo -e "    ${DIM}switch <nome>${NC}     Muda para branch"
    echo -e "    ${DIM}delete <nome>${NC}     Deleta branch"
    echo ""
    echo -e "  ${CYAN}log${NC} [n]            Mostra últimos n commits (default: 10)"
    echo -e "  ${CYAN}undo${NC} [ação]        Desfaz operações"
    echo -e "    ${DIM}commit${NC}            Desfaz último commit"
    echo -e "    ${DIM}staged${NC}            Remove do stage"
    echo -e "    ${DIM}changes${NC}           Descarta mudanças"
    echo ""
    echo -e "  ${CYAN}stash${NC} [ação]       Gerencia stashes"
    echo -e "    ${DIM}save [msg]${NC}        Guarda mudanças"
    echo -e "    ${DIM}pop${NC}               Restaura mudanças"
    echo -e "    ${DIM}list${NC}              Lista stashes"
    echo ""
    echo -e "  ${CYAN}release${NC} [versão]   Cria tag de release"
    echo -e "  ${CYAN}clean${NC}              Limpa branches e arquivos"
    echo ""
    echo -e "${WHITE}Exemplos:${NC}"
    echo ""
    echo -e "  ${DIM}# Commit rápido com push${NC}"
    echo "  ./scripts/git-helper.sh quick 'fix: corrige bug X'"
    echo ""
    echo -e "  ${DIM}# Salvar mudanças sem push${NC}"
    echo "  ./scripts/git-helper.sh save 'feat: nova feature'"
    echo ""
    echo -e "  ${DIM}# Criar nova branch${NC}"
    echo "  ./scripts/git-helper.sh branch new feature/nova-funcionalidade"
    echo ""
    echo -e "  ${DIM}# Criar release${NC}"
    echo "  ./scripts/git-helper.sh release v1.0.0"
    echo ""
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

cd "$PROJECT_ROOT"
check_git_repo

case "${1:-help}" in
    status|st|s)        cmd_status ;;
    save|commit|c)      cmd_save "$2" "$3" ;;
    quick|q)            cmd_quick "$2" ;;
    push|p)             cmd_push ;;
    pull|pl)            cmd_pull ;;
    sync)               cmd_sync ;;
    branch|br|b)        cmd_branch "$2" "$3" ;;
    log|l)              cmd_log "$2" ;;
    undo|u)             cmd_undo "$2" ;;
    stash)              cmd_stash "$2" "$3" ;;
    release|rel)        cmd_release "$2" ;;
    clean)              cmd_clean ;;
    help|--help|-h|"")  show_help ;;
    *)
        print_error "Comando desconhecido: $1"
        echo "Use './scripts/git-helper.sh help' para ver os comandos disponíveis."
        exit 1
        ;;
esac
