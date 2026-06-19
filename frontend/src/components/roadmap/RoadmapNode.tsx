import styles from './LearningRoadmap.module.css';

export interface RoadmapNodeData {
  id: string;
  title: string;
  type: string;
  status: 'completed' | 'current' | 'locked' | 'in_progress' | 'not_started';
  estimatedHours: number;
  weightage: string;
  description: string;
}

interface Props {
  node: RoadmapNodeData;
  isLast: boolean;
  isRecommended: boolean;
  onComplete: (id: string) => void;
}

export default function RoadmapNode({ node, isLast, isRecommended, onComplete }: Props) {
  const getIcon = () => {
    switch (node.status) {
      case 'completed':
        return (
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        );
      case 'current':
      case 'in_progress':
        return (
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
        );
      default:
        return (
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
          </svg>
        );
    }
  };

  const statusClass = node.status === 'completed' ? styles.statusCompleted : 
                      (node.status === 'current' || node.status === 'in_progress') ? styles.statusCurrent : 
                      styles.statusLocked;

  return (
    <div className={`${styles.nodeWrapper} ${statusClass} ${isRecommended ? styles.recommendedNode : ''}`}>
      {!isLast && <div className={styles.connectorLine}></div>}
      
      <div className={styles.nodeIconWrapper}>
        {getIcon()}
      </div>
      
      <div className={`${styles.nodeCard} ${isRecommended ? styles.recommendedCard : ''}`} title={`Difficulty Weightage: ${node.weightage}`}>
        {isRecommended && (
          <div className={styles.recommendedHeader}>
            <span className={styles.recommendedBadge}>
              ⭐ Next Recommended Module
            </span>
          </div>
        )}
        
        <div className={styles.nodeHeader}>
          <h3 className={styles.nodeTitle}>{node.title}</h3>
          <span className={styles.nodeTypeBadge}>{node.type}</span>
        </div>
        
        <p className={styles.nodeDescription}>{node.description}</p>
        
        <div className={styles.nodeActionFooter}>
          <div className={styles.nodeMeta}>
            <div className={styles.metaItem}>
              <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              {node.estimatedHours} Hours
            </div>
            <div className={styles.metaItem}>
              <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
              </svg>
              Weightage: {node.weightage}
            </div>
          </div>
          
          <div className={styles.completeBtnWrapper}>
            {node.status === 'completed' ? (
              <span className={styles.completedBadge}>
                <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                Completed
              </span>
            ) : (
              <button 
                type="button"
                className={styles.completeBtn}
                onClick={() => onComplete(node.id)}
              >
                {node.id === 'u-17' ? 'Start Practice Session' : 'Mark as completed'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

