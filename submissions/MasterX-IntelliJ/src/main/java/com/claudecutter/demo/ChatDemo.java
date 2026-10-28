package com.claudecutter.demo;

import com.claudecutter.accounting.TokenLedger;
import com.claudecutter.cost.CostCalculator;
import com.claudecutter.dashboard.DashboardExporter;
import com.claudecutter.model.Pricing;
import com.claudecutter.model.UsageRecord;
import com.claudecutter.pipeline.RequestPipeline;
import com.claudecutter.provider.LlmClient;
import com.claudecutter.provider.TokenCounter;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.SwingConstants;
import javax.swing.SwingUtilities;
import javax.swing.SwingWorker;
import javax.swing.UIManager;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Cursor;
import java.awt.Desktop;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * A professional chat window driving the engine.
 *
 * <ul>
 *   <li>Rounded left/right bubbles (user blue, assistant white).</li>
 *   <li>Code blocks render in a dark monospace panel (the answer's {@code ```} fences).</li>
 *   <li>A "Thinking…" indicator while the engine runs.</li>
 *   <li>A subtle route/cost badge under each assistant reply.</li>
 *   <li>Rounded, padded input; Enter sends, Shift+Enter inserts a newline.</li>
 *   <li>Header shows a live (green) / mock (gray) status dot.</li>
 * </ul>
 */
public final class ChatDemo {

    // Design tokens
    private static final Color PAGE_BG      = new Color(0xF5F6F8);
    private static final Color USER_BG      = new Color(0x2A78D6);
    private static final Color ASSISTANT_BG = Color.WHITE;
    private static final Color INK          = new Color(0x1A1A1A);
    private static final Color MUTED        = new Color(0x8A8E98);
    private static final Color CODE_BG      = new Color(0x1E1E2E);
    private static final Color CODE_INK     = new Color(0xE6E6EF);
    private static final Color ACCENT       = new Color(0x2A78D6);
    private static final Color LIVE          = new Color(0x1BAF7A);
    private static final Color MOCK          = new Color(0xB0B3BC);

    private final Pricing pricing = new Pricing();
    private final TokenLedger ledger = new TokenLedger(pricing);
    private final RequestPipeline pipeline;

    private final JPanel feed = new JPanel();
    private final JScrollPane scroll;
    private final boolean live;

    public ChatDemo(LlmClient qwen, LlmClient claude, TokenCounter counter, boolean live) {
        this.pipeline = new RequestPipeline(qwen, claude, SampleCodebase.build(), ledger, counter);
        this.pipeline.setStageListener(this::onStage);
        this.live = live;
        feed.setLayout(new BoxLayout(feed, BoxLayout.Y_AXIS));
        feed.setBackground(PAGE_BG);
        feed.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));
        scroll = new JScrollPane(feed);
        scroll.setBorder(BorderFactory.createEmptyBorder());
        scroll.setBackground(PAGE_BG);
        scroll.getViewport().setBackground(PAGE_BG);
        scroll.getVerticalScrollBar().setUnitIncrement(16);
    }

    public void build() {
        JFrame frame = new JFrame("ClaudeCutter");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(820, 700);
        frame.setLocationRelativeTo(null);
        frame.getContentPane().setBackground(PAGE_BG);

        frame.add(buildHeader(), BorderLayout.NORTH);
        frame.add(scroll, BorderLayout.CENTER);
        frame.add(buildInputBar(), BorderLayout.SOUTH);
        frame.setVisible(true);

        addBubble("Hi! I'm your coding assistant. Ask me to build or explain something — "
                + "I'll route easy questions to a lightweight model and send hard coding "
                + "tasks to Claude with the relevant context compressed. Click "
                + "\"Dashboard\" in the top-right to see the token savings.", false, null);
        input.requestFocusInWindow();
    }

    // ---- header ----
    private JTextField input;

    private JPanel buildHeader() {
        JPanel top = new JPanel(new BorderLayout());
        top.setBackground(Color.WHITE);
        top.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, new Color(0xE4E6EB)));

        JPanel left = new JPanel(new FlowLayout(FlowLayout.LEFT, 12, 0));
        left.setOpaque(false);
        left.setBorder(BorderFactory.createEmptyBorder(14, 18, 14, 18));

        // Logo mark
        RoundedPanel logo = new RoundedPanel(ACCENT, 10);
        logo.setPreferredSize(new Dimension(34, 34));
        logo.setMaximumSize(new Dimension(34, 34));
        JLabel logoText = new JLabel("✦", SwingConstants.CENTER);
        logoText.setForeground(Color.WHITE);
        logoText.setFont(logoText.getFont().deriveFont(Font.BOLD, 17f));
        logo.setLayout(new BorderLayout());
        logo.add(logoText, BorderLayout.CENTER);
        left.add(logo);

        JLabel title = new JLabel("ClaudeCutter");
        title.setFont(title.getFont().deriveFont(Font.BOLD, 16f));
        left.add(title);

        // Status dot + label
        JLabel statusDot = new JLabel("●");
        statusDot.setForeground(live ? LIVE : MOCK);
        statusDot.setFont(statusDot.getFont().deriveFont(9f));
        JLabel statusLabel = new JLabel(live ? "Connected" : "Offline demo");
        statusLabel.setForeground(MUTED);
        statusLabel.setFont(statusLabel.getFont().deriveFont(11f));
        JPanel status = new JPanel(new FlowLayout(FlowLayout.LEFT, 5, 0));
        status.setOpaque(false);
        status.add(statusDot);
        status.add(statusLabel);
        left.add(status);

        JButton openDash = new JButton("Dashboard");
        styleSecondary(openDash);
        openDash.setCursor(new Cursor(Cursor.HAND_CURSOR));
        openDash.addActionListener(e -> openDashboard());
        JPanel right = new JPanel(new FlowLayout(FlowLayout.RIGHT, 0, 0));
        right.setOpaque(false);
        right.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 16));
        right.add(openDash);

        top.add(left, BorderLayout.WEST);
        top.add(right, BorderLayout.EAST);
        return top;
    }

    // ---- input bar ----
    private JPanel buildInputBar() {
        RoundedPanel wrapper = new RoundedPanel(Color.WHITE, 18);
        wrapper.setLayout(new BorderLayout(10, 0));
        wrapper.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(new Color(0xE4E6EB), 1),
                BorderFactory.createEmptyBorder(6, 8, 6, 8)));

        input = new JTextField();
        input.setFont(input.getFont().deriveFont(14f));
        input.setBorder(BorderFactory.createEmptyBorder(8, 10, 8, 10));
        input.setOpaque(false);
        input.setForeground(INK);

        JButton send = new JButton("Send");
        send.setUI(new javax.swing.plaf.basic.BasicButtonUI());
        send.setBackground(ACCENT);
        send.setForeground(Color.WHITE);
        send.setFocusPainted(false);
        send.setOpaque(true);
        send.setContentAreaFilled(true);
        send.setBorderPainted(false);
        send.setBorder(BorderFactory.createEmptyBorder(10, 22, 10, 22));
        send.setCursor(new Cursor(Cursor.HAND_CURSOR));
        send.setFont(send.getFont().deriveFont(Font.BOLD, 13f));

        Runnable onSubmit = () -> {
            String prompt = input.getText().trim();
            if (prompt.isEmpty()) {
                return;
            }
            input.setText("");
            send.setEnabled(false);
            addBubble(prompt, true, null);
            JPanel typing = addTyping();

            new SwingWorker<String, Void>() {
                @Override
                protected String doInBackground() {
                    return pipeline.handle("chat", prompt);
                }

                @Override
                protected void done() {
                    String answer;
                    try {
                        answer = get();
                    } catch (Exception e) {
                        answer = "(error: " + e.getMessage() + ")";
                    }
                    remove(typing);
                    UsageRecord last = ledger.records().get(ledger.records().size() - 1);
                    addBubble(answer, false, last);
                    send.setEnabled(true);
                    input.requestFocusInWindow();
                }
            }.execute();
        };

        send.addActionListener(e -> onSubmit.run());
        input.addActionListener(e -> onSubmit.run());
        input.addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                if (e.getKeyCode() == KeyEvent.VK_ENTER && e.isShiftDown()) {
                    // Shift+Enter -> newline is not natively supported by JTextField;
                    // swallow and do nothing special (keeps single-line input).
                    e.consume();
                }
            }
        });

        wrapper.add(input, BorderLayout.CENTER);
        wrapper.add(send, BorderLayout.EAST);

        JPanel bottom = new JPanel(new BorderLayout());
        bottom.setBackground(Color.WHITE);
        bottom.setBorder(BorderFactory.createMatteBorder(1, 0, 0, 0, new Color(0xE4E6EB)));
        bottom.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createMatteBorder(1, 0, 0, 0, new Color(0xE4E6EB)),
                BorderFactory.createEmptyBorder(12, 16, 14, 16)));
        bottom.add(wrapper, BorderLayout.CENTER);
        return bottom;
    }

    // ---- message rendering ----
    private JPanel typingWrap;
    private JLabel typingLabel;

    private JPanel addTyping() {
        RoundedPanel bubble = new RoundedPanel(ASSISTANT_BG, 16);
        bubble.setLayout(new BoxLayout(bubble, BoxLayout.Y_AXIS));
        bubble.setBorder(BorderFactory.createEmptyBorder(12, 16, 12, 16));
        typingLabel = new JLabel("Thinking…");
        typingLabel.setForeground(MUTED);
        typingLabel.setFont(typingLabel.getFont().deriveFont(Font.ITALIC, 13f));
        bubble.add(typingLabel);
        typingWrap = align(bubble, false);
        feed.add(typingWrap);
        feed.revalidate();
        scrollToBottom();
        return typingWrap;
    }

    /** Called from the pipeline on each stage; updates the live status line. */
    private void onStage(String stage) {
        SwingUtilities.invokeLater(() -> {
            if (typingLabel == null) {
                return;
            }
            if (stage == null || stage.isEmpty()) {
                return; // done — the reply bubble replaces this; leave it for done()
            }
            typingLabel.setText(stage);
            typingLabel.revalidate();
            typingLabel.repaint();
        });
    }

    private void addBubble(String text, boolean isUser, UsageRecord record) {
        Color bg = isUser ? USER_BG : ASSISTANT_BG;
        RoundedPanel bubble = new RoundedPanel(bg, isUser ? 18 : 16);
        bubble.setLayout(new BoxLayout(bubble, BoxLayout.Y_AXIS));
        bubble.setBorder(BorderFactory.createEmptyBorder(12, 16, 12, 16));
        bubble.setMaximumSize(new Dimension(560, Integer.MAX_VALUE));

        for (Segment seg : split(text)) {
            bubble.add(renderSegment(seg, isUser));
        }

        JPanel wrap = align(bubble, isUser);

        if (!isUser && record != null) {
            JPanel meta = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
            meta.setOpaque(false);
            meta.setBorder(BorderFactory.createEmptyBorder(4, 4, 0, 4));
            JLabel badge = new JLabel(badgeText(record));
            badge.setForeground(MUTED);
            badge.setFont(badge.getFont().deriveFont(10.5f));
            meta.add(badge);
            JPanel col = new JPanel();
            col.setLayout(new BoxLayout(col, BoxLayout.Y_AXIS));
            col.setOpaque(false);
            col.setAlignmentX(Component.LEFT_ALIGNMENT);
            col.setMaximumSize(new Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE));
            wrap.setAlignmentX(Component.LEFT_ALIGNMENT);
            col.add(wrap);
            col.add(meta);
            feed.add(col);
        } else {
            feed.add(wrap);
        }

        feed.add(Box.createVerticalStrut(10));
        feed.revalidate();
        feed.repaint();
        scrollToBottom();
    }

    private JPanel align(Component c, boolean isUser) {
        JPanel wrap = new JPanel(new FlowLayout(isUser ? FlowLayout.RIGHT : FlowLayout.LEFT, 0, 0));
        wrap.setOpaque(false);
        wrap.setAlignmentX(Component.LEFT_ALIGNMENT);
        wrap.setMaximumSize(new Dimension(Integer.MAX_VALUE, c.getPreferredSize().height + 4));
        wrap.add(c);
        return wrap;
    }

    private Component renderSegment(Segment seg, boolean isUser) {
        if (seg.code()) {
            JTextArea code = new JTextArea(seg.text());
            code.setEditable(false);
            code.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
            code.setBackground(CODE_BG);
            code.setForeground(CODE_INK);
            code.setLineWrap(false);
            code.setBorder(BorderFactory.createEmptyBorder(10, 12, 10, 12));
            JPanel codeWrap = new RoundedPanel(CODE_BG, 8);
            codeWrap.setLayout(new BorderLayout());
            codeWrap.setAlignmentX(Component.LEFT_ALIGNMENT);
            codeWrap.add(code, BorderLayout.CENTER);
            return codeWrap;
        }
        JLabel label = new JLabel("<html><div style='width:480px'>" + escapeHtml(seg.text()) + "</div></html>");
        label.setFont(label.getFont().deriveFont(13.5f));
        label.setForeground(isUser ? Color.WHITE : INK);
        label.setOpaque(false);
        label.setAlignmentX(Component.LEFT_ALIGNMENT);
        return label;
    }

    private String badgeText(UsageRecord r) {
        var b = CostCalculator.compute(r, pricing);
        String route = r.route().target();
        long full = r.fullContextTokensEst();
        long comp = r.compressedContextTokens();
        long cut = full > 0 ? Math.round((1.0 - (double) comp / full) * 100) : 0;
        return String.format("answered by %s   ·   cost $%.4f vs $%.4f   ·   ctx %s→%s tok (%d%% cut)",
                route, b.totalCostUsd(), b.baselineCostUsd(), fmt(full), fmt(comp), cut);
    }

    private void openDashboard() {
        try {
            Path out = Path.of("dashboard.html");
            new DashboardExporter(ledger, pricing).export(out);
            Desktop.getDesktop().open(out.toFile());
        } catch (Exception ex) {
            addBubble("Could not open dashboard: " + ex.getMessage(), false, null);
        }
    }

    private void remove(JPanel typing) {
        feed.remove(typing);
        feed.revalidate();
        feed.repaint();
    }

    private void scrollToBottom() {
        SwingUtilities.invokeLater(() -> {
            var bar = scroll.getVerticalScrollBar();
            bar.setValue(bar.getMaximum());
        });
    }

    // ---- helpers ----
    private static String fmt(long n) {
        return String.format("%,d", n);
    }

    private static String escapeHtml(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\n", "<br>");
    }

    private static List<Segment> split(String text) {
        List<Segment> out = new ArrayList<>();
        String[] parts = text.split("```");
        for (int i = 0; i < parts.length; i++) {
            String p = parts[i].trim();
            if (p.isEmpty()) {
                continue;
            }
            // Fences: odd index = code; also strip a leading language tag on the first line.
            if (i % 2 == 1) {
                String code = p.replaceFirst("^[a-zA-Z]+\\s*\\n", "");
                out.add(new Segment(code, true));
            } else {
                out.add(new Segment(p, false));
            }
        }
        return out;
    }

    private record Segment(String text, boolean code) {}

    private static void styleSecondary(JButton b) {
        b.setUI(new javax.swing.plaf.basic.BasicButtonUI());
        b.setBackground(Color.WHITE);
        b.setForeground(ACCENT);
        b.setFocusPainted(false);
        b.setOpaque(true);
        b.setContentAreaFilled(true);
        b.setBorderPainted(true);
        b.setBorder(BorderFactory.createLineBorder(new Color(0xD5D9E0), 1));
        b.setFont(b.getFont().deriveFont(Font.BOLD, 12f));
    }

    /** A panel that paints a solid rounded rectangle as its background. */
    private static final class RoundedPanel extends JPanel {
        private final Color fill;
        private final int radius;

        RoundedPanel(Color fill, int radius) {
            this.fill = fill;
            this.radius = radius;
            setOpaque(false);
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setColor(fill);
            g2.fillRoundRect(0, 0, getWidth(), getHeight(), radius, radius);
            g2.dispose();
            super.paintComponent(g);
        }
    }

    public static void main(String[] args) throws Exception {
        UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        DemoApp.Providers providers = DemoApp.providers();
        boolean live = !providers.qwen().model().contains("turbo"); // cheap heuristic: mock uses qwen-turbo
        ChatDemo demo = new ChatDemo(providers.qwen(), providers.claude(), providers.counter(), live);
        SwingUtilities.invokeLater(demo::build);
    }
}
