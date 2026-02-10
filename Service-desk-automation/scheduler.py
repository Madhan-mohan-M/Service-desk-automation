"""
Background scheduler for automatic email processing.
Uses APScheduler for periodic tasks.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import config


class AutomationScheduler:
    """Manages background jobs for email processing and SLA checks."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._started = False
    
    def start(self, process_func, sla_check_func=None):
        """Start the scheduler with the given processing functions."""
        if self._started:
            return
        
        if config.AUTO_PROCESS_ENABLED:
            # Job 1: Process incoming emails
            self.scheduler.add_job(
                func=process_func,
                trigger=IntervalTrigger(seconds=config.POLL_INTERVAL_SECONDS),
                id='email_processor',
                name='Process incoming emails',
                replace_existing=True
            )
            print(f"[Scheduler] Email processing every {config.POLL_INTERVAL_SECONDS}s")
            
            # Job 2: Check SLA breaches
            if sla_check_func:
                self.scheduler.add_job(
                    func=sla_check_func,
                    trigger=IntervalTrigger(minutes=5),
                    id='sla_checker',
                    name='Check SLA breaches',
                    replace_existing=True
                )
                print("[Scheduler] SLA checking every 5 minutes")
            
            self.scheduler.start()
            self._started = True
            
            # Shut down scheduler when app exits
            atexit.register(self.shutdown)
        else:
            print("[Scheduler] Auto-processing disabled (set AUTO_PROCESS=true to enable)")
    
    def shutdown(self):
        """Gracefully shut down the scheduler."""
        if self._started:
            self.scheduler.shutdown()
            self._started = False
    
    def trigger_now(self, job_id: str = 'email_processor'):
        """Manually trigger a job immediately."""
        if self._started:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=None)  # run now
    
    def get_jobs_status(self) -> list:
        """Get status of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': str(job.next_run_time) if job.next_run_time else 'paused'
            })
        return jobs


# Singleton instance
automation_scheduler = AutomationScheduler()
