import styles from './Threads.module.css';

export default function SkeletonLoader() {
  return (
    <div className={styles.threadsList}>
      {[1, 2, 3].map(i => (
        <div key={i} className={styles.skeletonCard}>
          <div className={styles.skeletonVote}>
            <div className={styles.skeletonVoteInner}></div>
            <div className={styles.skeletonVoteInner} style={{ width: '10px', height: '10px' }}></div>
          </div>
          <div className={styles.skeletonBody}>
            <div className={styles.skeletonLine} style={{ width: '25%' }}></div>
            <div className={styles.skeletonLine} style={{ width: '85%' }}></div>
            <div className={styles.skeletonLine} style={{ width: '50%', height: '10px' }}></div>
          </div>
        </div>
      ))}
    </div>
  );
}
