const {
  SlashCommandBuilder,
  PermissionFlagsBits,
  EmbedBuilder,
} = require('discord.js');
const fs = require('node:fs');
const path = require('node:path');

// Module discord.js v14 pour la Chasse aux indices d'Halloween.
// Dans le fichier principal :
//   const halloween = require('./HalloweenClueHunt');
//   client.commands.set(halloween.data.name, halloween);
//   client.on('interactionCreate', interaction => halloween.execute(interaction));
// Adapte cette intégration si ton gestionnaire de commandes utilise déjà un routeur.

const DATA_FILE = path.join(__dirname, 'halloween-events.json');
const events = loadEvents();

function loadEvents() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch {
    return {};
  }
}

function saveEvents() {
  fs.writeFileSync(DATA_FILE, JSON.stringify(events, null, 2));
}

function eventFor(guildId) {
  return events[guildId];
}

function isStaff(interaction) {
  return interaction.memberPermissions?.has(PermissionFlagsBits.ManageGuild);
}

function clean(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function formatDate(timestamp) {
  return `<t:${timestamp}:F> (<t:${timestamp}:R>)`;
}

function sortedIndices(event) {
  return [...event.indices].sort((a, b) => a.number - b.number);
}

function makeAnnouncement(event) {
  return new EmbedBuilder()
    .setColor(0xff7518)
    .setTitle(`🎃 ${event.name}`)
    .setDescription(event.description || 'Retrouvez les indices cachés et résolvez les énigmes !')
    .addFields(
      { name: '📅 Début', value: formatDate(event.startAt) },
      { name: '🧩 Indices', value: String(event.indices.length), inline: true },
      { name: '👥 Participants', value: String(Object.keys(event.participants).length), inline: true },
    )
    .setFooter({ text: 'Utilisez /halloween chasse rejoindre pour participer.' });
}

const data = new SlashCommandBuilder()
  .setName('halloween')
  .setDescription('Mini-jeux d’Halloween')
  .addSubcommandGroup(group => group
    .setName('chasse')
    .setDescription('Gérer la chasse aux indices')
    .addSubcommand(command => command
      .setName('creer')
      .setDescription('Créer une chasse')
      .addStringOption(option => option.setName('nom').setDescription('Nom de la chasse').setRequired(true))
      .addIntegerOption(option => option.setName('date').setDescription('Date de début en timestamp Unix').setRequired(true))
      .addStringOption(option => option.setName('description').setDescription('Description de la chasse').setRequired(false)))
    .addSubcommand(command => command
      .setName('ajouter-indice')
      .setDescription('Ajouter ou remplacer un indice')
      .addIntegerOption(option => option.setName('numero').setDescription('Numéro de l’indice').setMinValue(1).setRequired(true))
      .addStringOption(option => option.setName('question').setDescription('Énigme affichée au joueur').setRequired(true))
      .addStringOption(option => option.setName('reponse').setDescription('Réponse correcte').setRequired(true))
      .addStringOption(option => option.setName('aide').setDescription('Aide facultative').setRequired(false))
      .addChannelOption(option => option.setName('salon').setDescription('Salon où chercher cet indice').setRequired(false)))
    .addSubcommand(command => command.setName('lancer').setDescription('Lancer la chasse maintenant'))
    .addSubcommand(command => command.setName('rejoindre').setDescription('Participer à la chasse'))
    .addSubcommand(command => command.setName('quitter').setDescription('Quitter la chasse'))
    .addSubcommand(command => command
      .setName('repondre')
      .setDescription('Répondre à l’indice actuel')
      .addStringOption(option => option.setName('reponse').setDescription('Ta réponse').setRequired(true)))
    .addSubcommand(command => command.setName('progression').setDescription('Voir sa progression'))
    .addSubcommand(command => command.setName('classement').setDescription('Voir le classement'))
    .addSubcommand(command => command.setName('terminer').setDescription('Terminer la chasse').setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild))
    .addSubcommand(command => command.setName('annuler').setDescription('Annuler la chasse').setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild))
  );

async function execute(interaction) {
  if (!interaction.isChatInputCommand() || interaction.commandName !== 'halloween') return;
  if (!interaction.guild) return interaction.reply({ content: 'Cette commande doit être utilisée sur un serveur.', ephemeral: true });

  const subcommand = interaction.options.getSubcommand();
  const event = eventFor(interaction.guildId);
  const staffCommands = ['creer', 'ajouter-indice', 'lancer', 'terminer', 'annuler'];

  if (staffCommands.includes(subcommand) && !isStaff(interaction)) {
    return interaction.reply({ content: '❌ Cette commande est réservée au staff.', ephemeral: true });
  }

  if (subcommand === 'creer') {
    if (event && event.status !== 'finished' && event.status !== 'cancelled') {
      return interaction.reply({ content: '❌ Une chasse est déjà configurée sur ce serveur.', ephemeral: true });
    }
    events[interaction.guildId] = {
      name: interaction.options.getString('nom'),
      description: interaction.options.getString('description') || '',
      startAt: interaction.options.getInteger('date'),
      status: 'setup',
      indices: [],
      participants: {},
      winners: [],
    };
    saveEvents();
    return interaction.reply({ content: `✅ Chasse créée. Ajoute les indices puis lance-la avec \\`/halloween chasse lancer\\` (début prévu : ${formatDate(events[interaction.guildId].startAt)}).` });
  }

  if (!event) return interaction.reply({ content: '❌ Aucune chasse n’est configurée.', ephemeral: true });

  if (subcommand === 'ajouter-indice') {
    if (event.status !== 'setup') return interaction.reply({ content: '❌ Les indices ne peuvent être modifiés qu’avant le lancement.', ephemeral: true });
    const indice = {
      number: interaction.options.getInteger('numero'),
      question: interaction.options.getString('question'),
      answer: clean(interaction.options.getString('reponse')),
      hint: interaction.options.getString('aide') || null,
      channelId: interaction.options.getChannel('salon')?.id || null,
    };
    event.indices = event.indices.filter(item => item.number !== indice.number);
    event.indices.push(indice);
    saveEvents();
    return interaction.reply({ content: `✅ Indice **${indice.number}** enregistré (${event.indices.length} indice(s)).`, ephemeral: true });
  }

  if (subcommand === 'lancer') {
    if (!event.indices.length) return interaction.reply({ content: '❌ Ajoute au moins un indice avant de lancer la chasse.', ephemeral: true });
    event.status = 'active';
    event.startedAt = Math.floor(Date.now() / 1000);
    saveEvents();
    return interaction.reply({ embeds: [makeAnnouncement(event)] });
  }

  if (subcommand === 'rejoindre') {
    if (event.status !== 'active') return interaction.reply({ content: '❌ La chasse n’est pas ouverte.', ephemeral: true });
    if (!event.participants[interaction.user.id]) {
      event.participants[interaction.user.id] = { username: interaction.user.username, index: 0, score: 0, joinedAt: Date.now(), finished: false };
      saveEvents();
    }
    return interaction.reply({ content: '🎃 Tu participes maintenant à la chasse ! Le premier indice sera révélé avec `/halloween chasse progression`.', ephemeral: true });
  }

  if (subcommand === 'quitter') {
    if (event.participants[interaction.user.id]) {
      delete event.participants[interaction.user.id];
      saveEvents();
    }
    return interaction.reply({ content: '✅ Tu as quitté la chasse.', ephemeral: true });
  }

  if (subcommand === 'repondre') {
    const player = event.participants[interaction.user.id];
    if (event.status !== 'active' || !player) return interaction.reply({ content: '❌ Tu ne participes pas à cette chasse.', ephemeral: true });
    const indices = sortedIndices(event);
    const current = indices[player.index];
    if (!current) return interaction.reply({ content: '🏆 Tu as déjà terminé la chasse !', ephemeral: true });
    if (clean(interaction.options.getString('reponse')) !== current.answer) {
      return interaction.reply({ content: '❌ Mauvaise réponse. Continue tes recherches !', ephemeral: true });
    }
    player.index += 1;
    player.score += 100;
    if (player.index >= indices.length) {
      player.finished = true;
      event.winners.push({ userId: interaction.user.id, username: interaction.user.username, finishedAt: Date.now() });
      saveEvents();
      return interaction.reply({ content: `🎉 Bravo ${interaction.user} ! Tu as terminé la chasse en **${event.winners.length}e position** et tu remportes **${player.score} points** !` });
    }
    saveEvents();
    return interaction.reply({ content: `✅ Bonne réponse ! Passe à l’indice **${indices[player.index].number}**.`, ephemeral: true });
  }

  if (subcommand === 'progression') {
    const player = event.participants[interaction.user.id];
    if (!player) return interaction.reply({ content: '❌ Tu dois d’abord rejoindre la chasse.', ephemeral: true });
    const current = sortedIndices(event)[player.index];
    return interaction.reply({ content: current ? `🕯️ Progression : **${player.index}/${event.indices.length}**\nIndice actuel : ${current.question}${current.channelId ? `\nCherche dans <#${current.channelId}>.` : ''}` : `🏆 Chasse terminée avec ${player.score} points !`, ephemeral: true });
  }

  if (subcommand === 'classement') {
    const ranking = Object.values(event.participants).sort((a, b) => b.index - a.index || b.score - a.score).slice(0, 10);
    const text = ranking.length ? ranking.map((player, i) => `${i + 1}. **${player.username}** — ${player.index}/${event.indices.length} indices — ${player.score} points`).join('\n') : 'Aucun participant.';
    return interaction.reply({ embeds: [new EmbedBuilder().setColor(0xff7518).setTitle('🏆 Classement Halloween').setDescription(text)] });
  }

  if (subcommand === 'terminer' || subcommand === 'annuler') {
    event.status = subcommand === 'terminer' ? 'finished' : 'cancelled';
    saveEvents();
    return interaction.reply({ content: subcommand === 'terminer' ? '✅ La chasse est terminée.' : '🛑 La chasse a été annulée.' });
  }
}

module.exports = { data, execute };
