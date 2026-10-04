package devpilot.backend.entity;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * One execution of the LangGraph "Issue Resolution Agent" against a GitHub issue.
 * The graph itself runs in the Python {@code agent-service}; this entity is the
 * durable record Java owns (issue reference, GitHub token access, final proposal).
 */
@Entity
@Table(name = "agent_runs")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AgentRun {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id", nullable = false)
    private UUID userId;

    @Column(name = "repository_id", nullable = false)
    private UUID repositoryId;

    @Column(name = "issue_number", nullable = false)
    private int issueNumber;

    @Column(name = "issue_title", nullable = false, length = 500)
    private String issueTitle;

    @Column(name = "issue_url", length = 500)
    private String issueUrl;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private AgentRunStatus status = AgentRunStatus.PENDING;

    @Column(name = "issue_type", length = 30)
    private String issueType;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Column(name = "root_cause", columnDefinition = "TEXT")
    private String rootCause;

    /** JSON array of plan step strings. */
    @Column(name = "plan_json", columnDefinition = "TEXT")
    private String planJson;

    @Column(name = "proposed_diff", columnDefinition = "TEXT")
    private String proposedDiff;

    @Column(name = "pr_description", columnDefinition = "TEXT")
    private String prDescription;

    @Column(name = "test_suggestions", columnDefinition = "TEXT")
    private String testSuggestions;

    @Column(name = "review_feedback", columnDefinition = "TEXT")
    private String reviewFeedback;

    @Column(length = 20)
    private String confidence;

    @Column(nullable = false)
    @Builder.Default
    private int iterations = 0;

    @Column(name = "github_comment_posted", nullable = false)
    @Builder.Default
    private boolean githubCommentPosted = false;

    @Column(name = "github_comment_url", length = 500)
    private String githubCommentUrl;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @PrePersist
    void onCreate() {
        Instant now = Instant.now();
        if (createdAt == null) {
            createdAt = now;
        }
        updatedAt = now;
        if (status == null) {
            status = AgentRunStatus.PENDING;
        }
    }

    @PreUpdate
    void onUpdate() {
        updatedAt = Instant.now();
    }
}
